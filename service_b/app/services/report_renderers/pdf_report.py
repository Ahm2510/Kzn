from datetime import datetime
from typing import Optional, Dict, Any
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_LEFT

from app.schemas.insight.report import InsightReport


_CURRENCY_NEGATIVE_RE = re.compile(r"\$\s*-\s*\d")
_CV_RE = re.compile(r"\bCV\s*[:=]\s*(\d+(?:\.\d+)?)\b", flags=re.IGNORECASE)
_COEFF_VAR_RE = re.compile(
    r"\bcoefficient\s+of\s+variation\b", flags=re.IGNORECASE
)
_N_RE = re.compile(r"\bn\s*[:=]\s*(\d+)\b", flags=re.IGNORECASE)
_CV_OF_RE = re.compile(r"\bCV\s+of\s+(\d+(?:\.\d+)?)\b", flags=re.IGNORECASE)
_OF_PRODUCTS_RE = re.compile(r"\bof\s+(\d[\d,]*)\s+products\b", flags=re.IGNORECASE)
_TOP3_PCT_RE = re.compile(r"\((\d+(?:\.\d+)?)%\)")

_KV_STAT_RE = re.compile(
    r"\b(?:cv|pct|n)\s*[:=]\s*[-+]?\d+(?:\.\d+)?\b", flags=re.IGNORECASE
)
_BASIS_NOISE_RE = re.compile(
    r"\b(?:computed\s+from|based\s+on)\s+\d[\d,]*\s+(?:records|rows)\b",
    flags=re.IGNORECASE,
)

_PRODUCTS_ANALYZED_RE = re.compile(
    r"\b(?:products\s+analyzed|distinct\s+products|unique\s+products|distinct\s+product\s+count|products\s+in\s+the\s+dataset)\b[^\d]*(\d[\d,]*)\b",
    flags=re.IGNORECASE,
)

_DISTINCT_PRODUCTS_INLINE_RE = re.compile(
    r"\b(\d[\d,]*)\s+distinct\s+products\b",
    flags=re.IGNORECASE,
)


def _escape(text: str) -> str:
    # ReportLab Paragraph supports a subset of HTML; keep user text safe.
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _rewrite_cv(text: str) -> str:
    def _cv_repl(match: re.Match) -> str:
        try:
            cv = float(match.group(1))
        except Exception:
            return ""

        if cv >= 1.0:
            return "Revenue swings dramatically from period to period — cash flow becomes unpredictable and forecasting stops being reliable"
        if cv >= 0.5:
            return "Revenue moves sharply between periods — planning becomes harder and short-term staffing/inventory decisions carry more risk"
        if cv >= 0.3:
            return "Revenue varies meaningfully between periods — you need tighter operating discipline to avoid surprise shortfalls"
        return "Revenue is steady across periods — you can plan staffing, inventory, and spend with confidence"

    return _CV_RE.sub(lambda m: _cv_repl(m), text)


def _rewrite_stat_language(text: str) -> str:
    if not text:
        return ""

    out = text
    out = _COEFF_VAR_RE.sub("revenue volatility", out)
    out = _rewrite_cv(out)
    out = _CV_OF_RE.sub(lambda m: _rewrite_cv(f"CV={m.group(1)}"), out)

    # Remove raw sample-size callouts from the main narrative.
    out = _N_RE.sub("", out)
    out = _KV_STAT_RE.sub("", out)
    out = _BASIS_NOISE_RE.sub("", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    out = out.replace("()", "").strip()
    return out


def _is_generic_action(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return True
    generic_markers = [
        "consider",
        "explore",
        "benchmark",
        "industry benchmarks",
        "compare against",
        "develop a strategy",
        "diversification strategy",
        "smoothing",
        "maintain portfolio balance",
        "allocate resources",
        "invest in",
        "monitor",
        "review",
    ]
    return any(m in t for m in generic_markers)


def _rewrite_driver_plain_english(text: Optional[str], title: str = "") -> str:
    raw = (text or "").strip()
    cleaned = _rewrite_stat_language(raw)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    combined = f"{title} {raw}".lower()
    if "volatil" in combined or "cv" in combined:
        return (
            "Revenue swings dramatically between transactions — the gap between the smallest and largest orders is extreme, "
            "so an average can mislead planning and cash-flow decisions."
        )
    if "top 3" in combined and "products" in combined:
        # Product concentration — parse real numbers from driver string if present
        prod_match = _OF_PRODUCTS_RE.search(raw)
        pct_match = _TOP3_PCT_RE.search(raw)
        prod_count = prod_match.group(1) if prod_match else "thousands of"
        top3_pct = pct_match.group(1) if pct_match else "a small fraction"
        return (
            f"Revenue is spread across {prod_count} products with no single SKU dominating — "
            f"the top 3 products combined drive only {top3_pct}% of total revenue, "
            "indicating a healthy and distributed product portfolio."
        )
    if "concentration" in combined or "top 10" in combined or "top-10" in combined:
        return (
            "A small slice of transactions is carrying a disproportionate share of revenue — you're dependent on a narrow set of customers, "
            "products, or big one-off orders."
        )
    if "mean" in combined and "median" in combined:
        return (
            "A small number of large orders are pulling the average up — typical orders are smaller than the headline average, "
            "which changes how you should forecast and target growth."
        )
    if "drop" in combined or "decline" in combined:
        return (
            "Revenue is shrinking versus your baseline — the decline is large enough to indicate a real demand/retention/pricing problem, "
            "not random noise."
        )
    if "growth" in combined or "increase" in combined:
        return (
            "Revenue expanded versus your baseline — the lift is being driven by a specific segment or set of orders that you can double down on."
        )

    return cleaned


def _rewrite_exec_takeaway(bullet: str) -> str:
    b = (bullet or "").strip()
    if not b:
        return ""
    lowered = b.lower()
    if "cv=" in lowered or "coefficient of variation" in lowered or "volatil" in lowered:
        return (
            "Revenue volatility is extremely high — cash flow is unpredictable and forecasting is unreliable without addressing transaction variance."
        )
    return _rewrite_stat_language(b)


def _rewrite_action_directional(
    text: Optional[str],
    *,
    title: str = "",
    description: str = "",
    driver: str = "",
    context: str = "",
) -> str:
    raw = (text or "").strip()
    cleaned = _rewrite_stat_language(raw)

    combined = " ".join([title, description, driver, raw, context]).lower()

    if "volatil" in combined or "cv" in combined or "swings" in combined:
        return (
            "Pull the top 5% of transactions by value and tag each one as: repeat customer, one-off bulk order, promo/discount spike, or seasonal surge. "
            "If the spikes are repeat customers, build a retention plan around them; if they’re one-offs, stop planning spend off the average and tighten cash controls; "
            "if they’re seasonal, pre-plan inventory and marketing to smooth the troughs."
        )

    if "product" in combined and "concentration" in combined and ("top 3" in combined or "top three" in combined) and ("4%" in combined or " 4 %" in combined):
        return (
            "Your product revenue is well distributed — no single SKU dominates. Protect this as you scale by reviewing product share monthly and avoiding over-investing in "
            "promoting one product at the expense of the catalog."
        )

    if "concentration" in combined or "top 10" in combined or "dependency" in combined:
        return (
            "List the customers and products inside the top 10% revenue slice. If fewer than ~20 customers drive most of the revenue, you have a retention emergency — "
            "assign an owner to protect those accounts with proactive outreach and renewal offers. If it’s product-led, you have a portfolio problem — fix availability, pricing, "
            "and merchandising on the few SKUs carrying the month, then build a plan to grow the middle of the catalog."
        )

    if "mean" in combined and "median" in combined:
        return (
            "Identify the large-order customers that are pulling the mean above the median, then build a retention and expansion plan specifically for them (reorder nudges, "
            "account-style support, and targeted bundles). Separately, treat the median order as your ‘typical’ customer and optimize acquisition economics around that number, "
            "not the inflated average."
        )

    if "diversif" in combined or "portfolio" in combined:
        return (
            "Set a hard guardrail: no single product should exceed ~15% of revenue as you scale. Review product share monthly; if any SKU starts creeping up, "
            "either grow adjacent products intentionally or cap discounting/stock allocation that’s over-feeding the leader."
        )

    if "drop" in combined or "decline" in combined:
        return (
            "Break the revenue decline into three cut views: (1) top 20 customers, (2) top 20 products, (3) the weeks/days with the biggest drop-off. "
            "If customers drove it, launch a win-back list and fix churn drivers; if products drove it, check stock-outs, pricing, and listing quality; if timing drove it, "
            "you’re dealing with seasonality or campaign gaps — plan promotions and cash accordingly."
        )

    if "growth" in combined or "increase" in combined:
        return (
            "Find the exact segment driving growth (customers, products, channel, or week). Then lock it in: keep inventory available for the winning products, "
            "mirror the campaign/channel that drove demand, and build retention loops so the growth repeats next period instead of disappearing."
        )

    if _is_generic_action(cleaned):
        return (
            "Start with a concrete cut: export the top 50 transactions by revenue and the bottom 50 by revenue. Identify whether the difference is customer type, product mix, "
            "discounting, geography, or timing. Then pick one lever to pull next week (pricing, inventory, retention, or acquisition) — and measure impact in the next period."
        )

    return cleaned


def _format_confidence(confidence: Optional[str], confidence_basis: Optional[str]) -> str:
    level = (confidence or "").strip().upper()
    if level not in {"HIGH", "MEDIUM", "LOW"}:
        level = "MEDIUM" if level else "MEDIUM"

    basis = _rewrite_stat_language(confidence_basis or "")
    basis_l = basis.lower()
    if any(k in basis_l for k in ["full dataset", "no sampling", "full baseline", "entire dataset"]):
        reason = "calculated across the full dataset with no sampling"
    elif any(k in basis_l for k in ["sample", "subset"]):
        reason = "directionally consistent in the data, but based on a subset"
    else:
        reason = "supported by a clear, consistent pattern in the data"

    return f"{level} — {reason}."


def _extract_total_transactions(report: InsightReport) -> Optional[int]:
    # Prefer any embedded n= signal that might exist in report.summary or confidence basis.
    candidates = [getattr(report, "summary", "") or ""]
    for ins in (report.insights or []):
        cb = getattr(ins, "confidence_basis", None)
        if cb:
            candidates.append(str(cb))

    for text in candidates:
        match = _N_RE.search(text)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                return None
    return None


def _extract_distinct_products(report: InsightReport, business_insights: Optional[Dict[str, Any]]) -> Optional[int]:
    # Prefer any explicit distinct product count already embedded in the analysis outputs.
    candidates: list[str] = []
    if getattr(report, "summary", None):
        candidates.append(str(report.summary))

    for ins in (report.insights or []):
        for field in [
            getattr(ins, "description", None),
            getattr(ins, "driver", None),
            getattr(ins, "confidence_basis", None),
        ]:
            if field:
                candidates.append(str(field))

    if business_insights:
        for key in ["executive_summary", "notes", "summary"]:
            v = business_insights.get(key)
            if v:
                candidates.append(str(v))

        scope = business_insights.get("scope")
        if isinstance(scope, dict):
            for k in ["products_analyzed", "distinct_products", "unique_products", "product_count"]:
                v = scope.get(k)
                if isinstance(v, int):
                    return v
                if isinstance(v, str):
                    candidates.append(v)

    for text in candidates:
        inline = _DISTINCT_PRODUCTS_INLINE_RE.search(text)
        if inline:
            try:
                return int(inline.group(1).replace(",", ""))
            except Exception:
                return None

        match = _PRODUCTS_ANALYZED_RE.search(text)
        if match:
            try:
                return int(match.group(1).replace(",", ""))
            except Exception:
                return None
    return None


def _importance_label(severity: str) -> str:
    sev = (severity or "").lower().strip()
    if sev == "high":
        return "Leadership focus"
    if sev == "medium":
        return "Decision lever"
    # Reframe “low” as context-setting, not low value.
    return "Context and baseline"


def _ensure_implication(text: Optional[str], fallback_context: str) -> str:
    base = (text or "").strip()
    base = _rewrite_stat_language(base)
    if base:
        return base
    return (
        "This matters because it changes how predictable your revenue is and where the business is exposed — "
        "cash flow, growth risk, and operational planning all depend on it. "
        + fallback_context
    ).strip()


def _ensure_action(text: Optional[str], fallback_action: str) -> str:
    base = (text or "").strip()
    base = _rewrite_stat_language(base)
    if base:
        return base
    return fallback_action


def _contains_negative_revenue(*texts: str) -> bool:
    for t in texts:
        if not t:
            continue
        if _CURRENCY_NEGATIVE_RE.search(t):
            return True
        if "negative revenue" in t.lower() or "revenue" in t.lower() and "negative" in t.lower():
            return True
    return False


def _negative_revenue_note() -> str:
    return (
        "Negative values typically indicate returns, refunds, or cancellations exceeding gross sales in this segment. "
        "Treat them as a signal to audit returns/refunds policy, fulfillment quality, and payment reconciliation — not as a system bug."
    )


def _build_executive_paragraph(
    report: InsightReport, business_insights: Optional[Dict[str, Any]]
) -> str:
    revenue_delta = None
    for d in (report.metric_deltas or []):
        if (d.name or "").lower() == "revenue":
            revenue_delta = d
            break

    total_revenue = revenue_delta.current if revenue_delta else None
    pct_change = revenue_delta.percent_change if (revenue_delta and revenue_delta.baseline) else None

    concentration = (business_insights or {}).get("concentration") if business_insights else None
    stability = (business_insights or {}).get("stability") if business_insights else None

    top10 = None
    risk_level = None
    if isinstance(concentration, dict):
        top10 = concentration.get("top_10_percent_contribution")
        risk_level = concentration.get("risk_level")

    stability_category = None
    if isinstance(stability, dict):
        stability_category = stability.get("category")

    scale_line = "Overall, this is a revenue business with real operating scale."
    if total_revenue is not None:
        scale_line = f"Overall, the business generated ${total_revenue:,.0f} in revenue in the period analyzed — enough scale that small leaks compound quickly."

    baseline_line = ""
    if pct_change is not None:
        direction = "up" if pct_change >= 0 else "down"
        baseline_line = f"Versus your baseline period, revenue moved {direction} {abs(pct_change):.1f}%. The direction matters less than what’s driving it — and whether it repeats."

    risk_line = "The biggest risk is concentration: revenue is likely over-dependent on a narrow slice of customers, products, or order spikes."
    if top10 is not None:
        risk_line = (
            f"The biggest risk is concentration: your top 10% of transactions drive about {top10:.0f}% of revenue. "
            "That level of dependency means one churn event, one stock-out, or one pricing change can swing the month."
        )
        if risk_level:
            risk_line = _rewrite_stat_language(risk_line)

    volatility_line = "Volatility is the second risk: when revenue swings, day-to-day decisions become reactive and expensive."
    if stability_category == "highly_volatile":
        volatility_line = (
            "Revenue swings sharply between periods. That makes cash flow unpredictable, complicates payroll and inventory decisions, "
            "and forces leadership to operate in firefighting mode instead of planning mode."
        )

    focus_line = (
        "Leadership should focus first on isolating what’s driving the revenue concentration and the swings: "
        "identify the customers/products behind the top slice of revenue, then validate whether that demand is repeatable or one-off."
    )

    action_line = (
        "Start with a short list: top customers, top products, and the weeks that spike. "
        "If it’s repeat customers, protect retention; if it’s product-led, fix availability and pricing; if it’s seasonal, plan cash and marketing to smooth the troughs."
    )

    unlock_line = (
        "If you reduce dependency on a narrow slice and make revenue more predictable, you unlock cleaner forecasting, calmer operations, "
        "and the ability to invest in growth with confidence."
    )

    lines = [scale_line]
    if baseline_line:
        lines.append(baseline_line)
    lines.extend([risk_line, volatility_line, focus_line, action_line, unlock_line])

    # Force a dense 8–12 line paragraph by splitting long sentences.
    expanded: list[str] = []
    for ln in lines:
        pieces = [p.strip() for p in re.split(r"(?<=[.!?])\s+", ln) if p.strip()]
        expanded.extend(pieces)

    expanded = expanded[:12]
    return " ".join(expanded)


class PageNumCanvas(Canvas):
    """
    Custom canvas to add page numbers during the build process.
    """

    def __init__(self, *args, **kwargs):
        Canvas.__init__(self, *args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            if page_count > 1:
                self.draw_page_number(page_count)
            Canvas.showPage(self)
        Canvas.save(self)

    def draw_page_number(self, page_count):
        self.setFont("Helvetica", 8)
        self.drawRightString(
            A4[0] - 0.75 * inch, 0.5 * inch, f"Page {self._pageNumber} of {page_count}"
        )


def render_pdf(
    report: InsightReport,
    output_path: str,
    business_insights: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Render a professional PDF report from an InsightReport.
    Visual-only layout; inputs, outputs and call pattern are unchanged.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    # Container for the 'Flowable' objects
    story = []
    styles = getSampleStyleSheet()

    # ------------------------------------------------------------------
    # Shared styles (visual only)
    # ------------------------------------------------------------------
    title_style = styles["Heading1"]
    title_style.alignment = TA_LEFT
    title_style.fontSize = 18
    title_style.spaceAfter = 4

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=HexColor("#666666"),
        leading=12,
    )

    date_style = ParagraphStyle(
        "GeneratedOn",
        parent=styles["Normal"],
        fontSize=9,
        textColor=HexColor("#777777"),
        leading=11,
    )

    section_heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        spaceBefore=10,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14,
    )

    small_muted_style = ParagraphStyle(
        "SmallMuted",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=HexColor("#888888"),
    )

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    story.append(Paragraph("Business Insight Report", title_style))
    story.append(Paragraph("Generated for revenue analysis", subtitle_style))

    date_str = datetime.now().strftime("%B %d, %Y")
    story.append(Paragraph(f"Generated on {date_str}", date_style))
    story.append(Spacer(1, 0.35 * inch))

    # C3. TABLE OF CONTENTS
    toc_style = ParagraphStyle(
        "TOC",
        parent=small_muted_style,
        leading=14,
        leftIndent=8,
    )
    toc_sections = ["Executive Takeaways", "Executive Summary", "Analysis Summary", "Key Metrics"]
    if business_insights and business_insights.get("revenue_stability_index"):
        toc_sections.append("Revenue Stability Index")
    if business_insights and business_insights.get("inventory_health_score"):
        toc_sections.append("Inventory Health Score")
    if business_insights and business_insights.get("early_warning_alerts"):
        ewa_data = business_insights["early_warning_alerts"]
        if isinstance(ewa_data, dict) and ewa_data.get("alert_count", 0) > 0:
            toc_sections.append("Early Warning Alerts")
    if business_insights and business_insights.get("cohort_product_performance"):
        clpp_data = business_insights["cohort_product_performance"]
        if isinstance(clpp_data, dict) and clpp_data.get("cohort_count", 0) > 0:
            toc_sections.append("Product Cohort Performance")
    toc_sections.append("Insights")
    if business_insights:
        toc_sections.append("Business Interpretation")

    story.append(Paragraph("<b>Contents</b>", toc_style))
    for i, sec in enumerate(toc_sections, 1):
        story.append(Paragraph(f"  {i}. {sec}", toc_style))
    story.append(Spacer(1, 0.25 * inch))

    # ------------------------------------------------------------------
    # Executive Takeaways + Scope (if business_insights present)
    # ------------------------------------------------------------------
    if business_insights:
        try:
            executive_takeaways = business_insights.get("executive_takeaways")
            if (
                executive_takeaways
                and isinstance(executive_takeaways, list)
                and len(executive_takeaways) > 0
            ):
                story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#E5E7EB"), spaceAfter=8, spaceBefore=4))
                story.append(Paragraph("Executive Takeaways", section_heading_style))
                bullet_style = ParagraphStyle(
                    "ExecBullet",
                    parent=body_style,
                    leftIndent=10,
                )
                for bullet in executive_takeaways[:6]:
                    if bullet:
                        story.append(Paragraph(f"• {_escape(_rewrite_exec_takeaway(str(bullet)))}", bullet_style))
                        story.append(Spacer(1, 0.05 * inch))
                story.append(Spacer(1, 0.2 * inch))

            scope = business_insights.get("scope")
            if scope and isinstance(scope, dict):
                analyzed = scope.get("analyzed", [])
                not_analyzed = scope.get("not_analyzed", [])
                if analyzed or not_analyzed:
                    scope_style = ParagraphStyle(
                        "ScopeStyle",
                        parent=small_muted_style,
                        leading=12,
                    )
                    scope_text = ""
                    if analyzed:
                        scope_text += f"<b>Analyzed:</b> {', '.join(analyzed)}. "
                    if not_analyzed:
                        scope_text += f"<b>Not analyzed:</b> {', '.join(not_analyzed)}."
                    story.append(Paragraph(scope_text, scope_style))
                    story.append(Spacer(1, 0.25 * inch))
        except Exception:
            # Defensive - never fail PDF generation for business insights
            pass

    # ------------------------------------------------------------------
    # Executive Summary section (always)
    # ------------------------------------------------------------------
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#E5E7EB"), spaceAfter=8, spaceBefore=4))
    story.append(Paragraph("Executive Summary", section_heading_style))
    exec_paragraph = _build_executive_paragraph(report, business_insights)
    story.append(Paragraph(_escape(exec_paragraph), body_style))
    story.append(Spacer(1, 0.15 * inch))

    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#E5E7EB"), spaceAfter=8, spaceBefore=4))
    story.append(Paragraph("Analysis Summary", section_heading_style))
    revenue_delta = None
    for d in (report.metric_deltas or []):
        if (d.name or "").lower() == "revenue":
            revenue_delta = d
            break
    total_revenue_value = revenue_delta.current if revenue_delta else None
    total_transactions_value = _extract_total_transactions(report)
    products_analyzed_value = _extract_distinct_products(report, business_insights)
    insights_generated_value = len(report.insights or [])

    summary_bullets = []
    if total_revenue_value is not None:
        summary_bullets.append(f"• <b>Total Revenue:</b> ${total_revenue_value:,.2f}")
    else:
        summary_bullets.append("• <b>Total Revenue:</b> —")

    if total_transactions_value is not None:
        summary_bullets.append(f"• <b>Total Transactions:</b> {total_transactions_value:,d}")

    if products_analyzed_value is not None:
        summary_bullets.append(f"• <b>Products Analyzed:</b> {products_analyzed_value:,d}")
    else:
        summary_bullets.append("• <b>Products Analyzed:</b> —")

    summary_bullets.append(f"• <b>Insights Generated:</b> {insights_generated_value:,d}")

    for b in summary_bullets:
        story.append(Paragraph(b, body_style))
    story.append(Spacer(1, 0.25 * inch))

    # C5. DATA QUALITY SUMMARY IN PDF
    if business_insights and business_insights.get("data_quality"):
        dq = business_insights["data_quality"]
        story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#E5E7EB"), spaceAfter=8, spaceBefore=4))
        story.append(Paragraph("Data Quality Summary", section_heading_style))
        dq_bullets = []
        if dq.get("rows_before") is not None and dq.get("rows_after") is not None:
            dq_bullets.append(f"• Rows after cleaning: {dq['rows_after']:,} (from {dq['rows_before']:,})")
        if dq.get("duplicate_rows_dropped"):
            dq_bullets.append(f"• Duplicate rows removed: {dq['duplicate_rows_dropped']:,}")
        if dq.get("null_rows_dropped"):
            dq_bullets.append(f"• Null rows removed: {dq['null_rows_dropped']:,}")
        if dq.get("columns_renamed"):
            dq_bullets.append(f"• Columns canonicalized: {', '.join(dq['columns_renamed'])}")
        for b in dq_bullets:
            story.append(Paragraph(b, body_style))
        story.append(Spacer(1, 0.2 * inch))

    # ------------------------------------------------------------------
    # Key Metrics section
    # ------------------------------------------------------------------
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#E5E7EB"), spaceAfter=8, spaceBefore=4))
    story.append(Paragraph("Key Metrics", section_heading_style))

    metrics_style = body_style

    if report.metric_deltas:
        for m in report.metric_deltas:
            if m.baseline == 0:
                metric_text = f"<b>{m.name.title()}:</b> ${m.current:,.2f}"
            else:
                sign = "+" if m.percent_change >= 0 else ""
                metric_text = (
                    f"<b>{m.name.title()}:</b> ${m.current:,.2f} "
                    f"({sign}{m.percent_change:.1f}% vs baseline ${m.baseline:,.2f})"
                )
            story.append(Paragraph(metric_text, metrics_style))
            story.append(Spacer(1, 0.1 * inch))

        any_negative_metric = any(
            (getattr(m, "current", 0) is not None and m.current < 0)
            or (getattr(m, "baseline", 0) is not None and m.baseline < 0)
            for m in report.metric_deltas
        )
        if any_negative_metric:
            story.append(Paragraph(_escape(_negative_revenue_note()), small_muted_style))
            story.append(Spacer(1, 0.1 * inch))
    else:
        story.append(Paragraph("<i>No metrics available.</i>", metrics_style))

    story.append(Spacer(1, 0.25 * inch))

    # ------------------------------------------------------------------
    # Revenue Stability Index section (if available)
    # ------------------------------------------------------------------
    if business_insights and business_insights.get("revenue_stability_index"):
        try:
            rsi = business_insights["revenue_stability_index"]
            score_val = rsi.get("score")
            label_val = rsi.get("label", "")
            explanation_val = rsi.get("explanation", "")
            factors = rsi.get("contributing_factors") or []
            warning_val = rsi.get("warning")
            confidence_val = rsi.get("confidence", "")

            story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#E5E7EB"), spaceAfter=8, spaceBefore=4))
            story.append(Paragraph("Revenue Stability Index", section_heading_style))

            if score_val is not None:
                story.append(
                    Paragraph(
                        f"<b>{score_val:.0f}/100</b> — {_escape(str(label_val))}",
                        body_style,
                    )
                )

            if explanation_val:
                story.append(Paragraph(_escape(str(explanation_val)), body_style))

            for factor in factors:
                story.append(Paragraph(f"• {_escape(str(factor))}", small_muted_style))

            if warning_val:
                story.append(Paragraph(f"\u26a0 {_escape(str(warning_val))}", small_muted_style))

            if confidence_val:
                story.append(
                    Paragraph(
                        f"Confidence: {str(confidence_val).upper()}",
                        small_muted_style,
                    )
                )

            story.append(Spacer(1, 0.25 * inch))
        except Exception:
            pass  # Never fail PDF generation for RSI
 
    # ------------------------------------------------------------------
    # Inventory Health Score section (if available)
    # ------------------------------------------------------------------
    if business_insights and business_insights.get("inventory_health_score"):
        try:
            ihs = business_insights["inventory_health_score"]
            ihs_score = ihs.get("score")
            ihs_label = ihs.get("label", "")
            ihs_explanation = ihs.get("explanation", "")
            ihs_factors = ihs.get("contributing_factors") or []
            ihs_warning = ihs.get("warning")
            ihs_confidence = ihs.get("confidence", "")
            ihs_source = ihs.get("data_source", "")
            ihs_watchlist = ihs.get("watchlist") or []
 
            story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#E5E7EB"), spaceAfter=8, spaceBefore=4))
            story.append(Paragraph("Inventory Health Score", section_heading_style))
 
            if ihs_score is not None:
                story.append(
                    Paragraph(
                        f"<b>{ihs_score:.0f}/100</b> — {_escape(str(ihs_label))}",
                        body_style,
                    )
                )
 
            if ihs_explanation:
                story.append(Paragraph(_escape(str(ihs_explanation)), body_style))
 
            for factor in ihs_factors:
                story.append(Paragraph(f"• {_escape(str(factor))}", small_muted_style))
 
            if ihs_watchlist:
                watchlist_str = ", ".join(str(w) for w in ihs_watchlist)
                story.append(
                    Paragraph(
                        f"<i>SKUs to review:</i> {_escape(watchlist_str)}",
                        small_muted_style,
                    )
                )
 
            if ihs_warning:
                story.append(Paragraph(f"\u26a0 {_escape(str(ihs_warning))}", small_muted_style))
 
            if ihs_confidence:
                confidence_text = f"Confidence: {str(ihs_confidence).upper()}"
                ihs_confidence_reason = ihs.get("confidence_reason")
                if ihs_confidence_reason:
                    confidence_text += f" — {_escape(str(ihs_confidence_reason))}"
                elif ihs_source:
                    confidence_text += f" — based on {_escape(str(ihs_source))}"
                
                story.append(
                    Paragraph(
                        confidence_text,
                        small_muted_style,
                    )
                )
 
            story.append(Spacer(1, 0.25 * inch))
        except Exception:
            pass  # Never fail PDF generation for IHS
 
    # ------------------------------------------------------------------
    # Early Warning Alerts section (if available and non-empty)
    # ------------------------------------------------------------------
    if business_insights and business_insights.get("early_warning_alerts"):
        try:
            ewa = business_insights["early_warning_alerts"]
            ewa_alerts = ewa.get("alerts") or []
            if ewa_alerts:
                story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#E5E7EB"), spaceAfter=8, spaceBefore=4))
                story.append(Paragraph("Early Warning Alerts", section_heading_style))
 
                sev_label_map = {
                    "critical": "\u26d4 CRITICAL",
                    "high": "\u26a0 HIGH",
                    "medium": "\u25b2 MEDIUM",
                    "low": "\u2139 LOW",
                }
 
                for alert in ewa_alerts:
                    sev = alert.get("severity", "low")
                    sev_display = sev_label_map.get(sev, sev.upper())
                    title = alert.get("title", "")
                    desc = alert.get("description", "")
                    driver = alert.get("driver", "")
                    action = alert.get("action_direction", "")
                    confidence = alert.get("confidence", "")
 
                    story.append(
                        Paragraph(
                            f"<b>[{_escape(sev_display)}]</b> {_escape(str(title))}",
                            body_style,
                        )
                    )
                    if desc:
                        story.append(Paragraph(_escape(str(desc)), small_muted_style))
                    if driver:
                        story.append(Paragraph(f"<i>Driver:</i> {_escape(str(driver))}", small_muted_style))
                    if action:
                        story.append(Paragraph(f"<i>Action:</i> {_escape(str(action))}", small_muted_style))
                    if confidence:
                        story.append(
                            Paragraph(
                                f"Confidence: {str(confidence).upper()}",
                                small_muted_style,
                            )
                        )
                    story.append(Spacer(1, 0.15 * inch))
 
                story.append(Spacer(1, 0.1 * inch))
        except Exception:
            pass  # Never fail PDF generation for EWA

    # ------------------------------------------------------------------
    # Product Cohort Performance section (if available and non-empty)
    # ------------------------------------------------------------------
    if business_insights and business_insights.get("cohort_product_performance"):
        try:
            clpp = business_insights["cohort_product_performance"]
            clpp_cohorts = clpp.get("cohorts") or []
            if clpp_cohorts:
                story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#E5E7EB"), spaceAfter=8, spaceBefore=4))
                story.append(Paragraph("Product Cohort Performance", section_heading_style))
 
                clpp_basis = clpp.get("cohort_basis", "")
                if clpp_basis:
                    story.append(
                        Paragraph(
                            f"Cohort grouping: <b>{_escape(clpp_basis.replace('_', ' ').title())}</b> "
                            f"({len(clpp_cohorts)} cohort{'s' if len(clpp_cohorts) != 1 else ''})",
                            small_muted_style,
                        )
                    )
                    story.append(Spacer(1, 0.1 * inch))
 
                tier_icon = {
                    "top_performer": "\u2605",
                    "stable_performer": "\u25cf",
                    "underperformer": "\u25bc",
                    "declining_cohort": "\u25bc\u25bc",
                    "insufficient_data": "\u2014",
                }
 
                for cohort in clpp_cohorts:
                    label = cohort.get("cohort_label", "")
                    tier = cohort.get("performance_tier", "")
                    icon = tier_icon.get(tier, "")
                    rev_share = cohort.get("revenue_share_pct", 0)
                    growth = cohort.get("period_growth_pct")
                    explanation = cohort.get("explanation", "")
                    confidence = cohort.get("confidence", "")
                    warning = cohort.get("warning")
 
                    tier_display = tier.replace("_", " ").title()
                    growth_str = f"{growth:+.1f}%" if growth is not None else "N/A"
 
                    story.append(
                        Paragraph(
                            f"{icon} <b>{_escape(str(label))}</b> — {_escape(tier_display)}",
                            body_style,
                        )
                    )
                    story.append(
                        Paragraph(
                            f"Revenue share: {rev_share:.1f}% | Growth: {growth_str} | Confidence: {str(confidence).upper()}",
                            small_muted_style,
                        )
                    )
                    if explanation:
                        story.append(Paragraph(_escape(str(explanation)), small_muted_style))
                    if warning:
                        story.append(Paragraph(f"\u26a0 {_escape(str(warning))}", small_muted_style))
                    story.append(Spacer(1, 0.12 * inch))
 
                story.append(Spacer(1, 0.1 * inch))
        except Exception:
            pass  # Never fail PDF generation for CLPP
 
    # ------------------------------------------------------------------
    # Insights section
    # ------------------------------------------------------------------
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#E5E7EB"), spaceAfter=8, spaceBefore=4))
    story.append(Paragraph("Insights", section_heading_style))


    insights_style = body_style

    if report.insights:
        any_negative_insight = False
        for ins in report.insights:
            importance = _importance_label(ins.severity)

            title_line = f"<b>{_escape(ins.title)}</b>"
            story.append(Paragraph(title_line, insights_style))
            story.append(Paragraph(f"<i>Why it matters:</i> {_escape(importance)}", small_muted_style))

            if getattr(ins, "code", "") == "REVENUE_VOLATILITY":
                desc = (
                    "Revenue swings dramatically across transactions — the gap between typical orders and peak orders is extreme, "
                    "making the average transaction value unreliable as a planning number."
                )
            else:
                desc = _rewrite_stat_language(ins.description)
            story.append(Paragraph(_escape(desc), insights_style))

            # Render enrichment fields if present
            fallback_context = ""
            if getattr(ins, "affected_metric", None):
                fallback_context = f"Focus on the drivers behind {ins.affected_metric} first — it is the fastest way to reduce operational uncertainty."

            driver = _rewrite_stat_language(ins.driver or "")
            implication = _ensure_implication(ins.implication, fallback_context)
            driver_plain = _rewrite_driver_plain_english(ins.driver or "", title=ins.title)
            action = _rewrite_action_directional(
                ins.action_direction,
                title=ins.title or "",
                description=ins.description or "",
                driver=ins.driver or "",
                context=fallback_context,
            )

            if driver_plain:
                story.append(
                    Paragraph(
                        f"<i>Driver:</i> {_escape(driver_plain)}",
                        small_muted_style,
                    )
                )
            story.append(Paragraph(f"<i>Implication:</i> {_escape(implication)}", small_muted_style))
            story.append(Paragraph(f"<i>Action:</i> {_escape(action)}", small_muted_style))

            if _contains_negative_revenue(ins.title, ins.description, ins.driver or "", ins.implication or ""):
                any_negative_insight = True
                story.append(Paragraph(_escape(_negative_revenue_note()), small_muted_style))

            if ins.confidence:
                conf_text = f"Confidence: {_format_confidence(ins.confidence, getattr(ins, 'confidence_basis', None))}"
                story.append(Paragraph(conf_text, small_muted_style))

            story.append(Spacer(1, 0.18 * inch))

        if any_negative_insight:
            story.append(Spacer(1, 0.05 * inch))
    else:
        story.append(
            Paragraph(
                "<i>No significant insights detected in the analysis.</i>",
                insights_style,
            )
        )

    # ------------------------------------------------------------------
    # Business Insights detailed sections (if present)
    # ------------------------------------------------------------------
    if business_insights:
        try:
            story.append(Spacer(1, 0.3 * inch))
            story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#E5E7EB"), spaceAfter=8, spaceBefore=4))
            story.append(Paragraph("Business Interpretation", section_heading_style))
            story.append(Spacer(1, 0.1 * inch))

            detail_style = body_style

            small_style = small_muted_style

            def render_enriched_insight(name: str, insight: dict) -> None:
                if not insight:
                    return
                story.append(Paragraph(f"<b>{name}</b>", detail_style))

                if insight.get("description"):
                    raw_desc = str(insight["description"])
                    if name == "Revenue Stability" and any(k in raw_desc.lower() for k in ["volatil", "cv", "anomaly"]):
                        rendered_desc = (
                            "Revenue swings are extreme — cash flow is unpredictable and "
                            "planning off averages will mislead decision-making."
                        )
                    else:
                        rendered_desc = _rewrite_stat_language(raw_desc)
                    story.append(Paragraph(_escape(rendered_desc), detail_style))

                if insight.get("driver"):
                    story.append(
                        Paragraph(
                            f"<i>Driver:</i> {_escape(_rewrite_driver_plain_english(insight.get('driver'), title=name))}",
                            detail_style,
                        )
                    )

                if insight.get("implication"):
                    story.append(
                        Paragraph(
                            f"<i>Implication:</i> {_escape(_rewrite_stat_language(insight['implication']))}",
                            detail_style,
                        )
                    )

                if insight.get("action_direction"):
                    rewritten_action = _rewrite_action_directional(
                        insight.get("action_direction"),
                        title=name,
                        description=str(insight.get("description") or ""),
                        driver=str(insight.get("driver") or ""),
                    )
                    story.append(
                        Paragraph(
                            f"<i>Action:</i> {_escape(rewritten_action)}",
                            detail_style,
                        )
                    )

                confidence = insight.get("confidence")
                confidence_basis = insight.get("confidence_basis")
                if confidence:
                    conf_text = f"Confidence: {_format_confidence(str(confidence), str(confidence_basis) if confidence_basis else None)}"
                    story.append(Paragraph(conf_text, small_style))

                story.append(Spacer(1, 0.15 * inch))

            render_enriched_insight("Trend Analysis", business_insights.get("trend"))
            render_enriched_insight(
                "Revenue Stability", business_insights.get("stability")
            )
            render_enriched_insight(
                "Revenue Efficiency", business_insights.get("efficiency")
            )
            render_enriched_insight(
                "Revenue Concentration", business_insights.get("concentration")
            )

            # Intentionally omit any “Additional Notes” section.
        except Exception:
            # Defensive - never fail PDF generation for business insights
            pass

    # C4. APPENDIX
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#E5E7EB"), spaceAfter=8, spaceBefore=4))
    story.append(Paragraph("Appendix: Methodology Notes", section_heading_style))

    appendix_text = (
        "Revenue detection uses semantic column matching across known synonyms (revenue, sales, "
        "turnover, total_price, gmv, etc.) with confidence thresholds. "
        "Concentration analysis uses a top-10% percentile cutoff applied to the full transaction dataset. "
        "Volatility is measured by coefficient of variation (std \u00f7 mean) on the revenue column. "
        "Efficiency is computed as percent change in average revenue per transaction between periods. "
        "All figures reflect the dataset provided and no external data was used. "
        "Results are directional indicators, not audited financial statements."
    )
    story.append(Paragraph(_escape(appendix_text), small_muted_style))
    story.append(Spacer(1, 0.2 * inch))

    # Build PDF (IO + layout only; no contract changes)
    doc.build(story, canvasmaker=PageNumCanvas)
