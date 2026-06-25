from datetime import datetime
from typing import Optional, Dict, Any
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.enums import TA_LEFT

from app.schemas.insight.report import InsightReport
from app.services.insight_engine.entity_detector import (
    format_inr as _format_inr,
    format_inr_lakh as _format_inr_lakh,
)


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
            # Always show page numbers for professional reports
            self.draw_page_number(page_count)
            Canvas.showPage(self)
        Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        # Footer rule line
        y = 0.45 * inch
        self.setStrokeColor(HexColor("#E0E0E0"))
        self.setLineWidth(0.5)
        self.line(0.75 * inch, y + 10, A4[0] - 0.75 * inch, y + 10)
        
        # Left footer: Confidential
        self.setFont("Helvetica", 7)
        self.setFillColor(HexColor("#999999"))
        self.drawString(0.75 * inch, y, "Business Insight Report \u2022 Confidential")
        
        # Right footer: Page X of Y
        self.drawRightString(
            A4[0] - 0.75 * inch, y, f"Page {self._pageNumber} of {page_count}"
        )
        self.restoreState()


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
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        alignment=TA_LEFT,
        fontSize=22,
        textColor=HexColor("#1A1A1A"),
        spaceAfter=2,
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=HexColor("#555555"),
        leading=14,
    )

    date_style = ParagraphStyle(
        "GeneratedOn",
        parent=styles["Normal"],
        fontSize=9,
        textColor=HexColor("#999999"),
        leading=12,
        spaceAfter=6,
    )

    major_section_heading_style = ParagraphStyle(
        "MajorSectionHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=HexColor("#1A1A1A"),
        spaceBefore=16,
        spaceAfter=8,
        fontName="Helvetica-Bold",
    )

    section_heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=HexColor("#2C2C2C"),
        leading=16,
        spaceBefore=14,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=10,
        leading=15,
        spaceAfter=3,
    )

    label_style = ParagraphStyle(
        "LabelStyle",
        parent=styles["Normal"],
        fontSize=9,
        textColor=HexColor("#555555"),
        fontName="Helvetica-Bold",
        leading=12,
    )

    metric_value_style = ParagraphStyle(
        "MetricValue",
        parent=styles["Normal"],
        fontSize=11,
        textColor=HexColor("#1A1A1A"),
        fontName="Helvetica-Bold",
        leading=14,
    )

    small_muted_style = ParagraphStyle(
        "SmallMuted",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        textColor=HexColor("#777777"),
    )

    confidential_style = ParagraphStyle(
        "Confidential",
        parent=styles["Normal"],
        fontSize=7.5,
        textColor=HexColor("#AAAAAA"),
        fontName="Helvetica-Oblique",
        leading=9,
    )

    toc_entry_style = ParagraphStyle(
        "TOCEntry",
        parent=styles["Normal"],
        fontSize=9,
        leading=14,
        leftIndent=12,
        textColor=HexColor("#444444"),
    )

    # ------------------------------------------------------------------
    # Helper Constants: HR Tiers
    # ------------------------------------------------------------------
    HR_MAJOR = lambda: HRFlowable(width="100%", thickness=1.5, color=HexColor("#CCCCCC"), spaceAfter=10, spaceBefore=16)
    HR_STANDARD = lambda: HRFlowable(width="100%", thickness=0.75, color=HexColor("#E0E0E0"), spaceAfter=8, spaceBefore=12)
    HR_MINOR = lambda: HRFlowable(width="100%", thickness=0.3, color=HexColor("#EEEEEE"), spaceAfter=4, spaceBefore=6)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    # Thick accent bar at top
    story.append(HRFlowable(width="100%", thickness=3, color=HexColor("#2C2C2C"), spaceAfter=12, spaceBefore=0))
    story.append(Paragraph("Business Insight Report", title_style))
    story.append(Paragraph("Revenue Analysis \u2022 Confidential", subtitle_style))
    
    date_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    story.append(Paragraph(f"Report generated: {date_str}", date_style))
    
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#E5E7EB"), spaceAfter=4, spaceBefore=10))
    story.append(Spacer(1, 0.2 * inch))

    # Table of Contents
    story.append(Paragraph("Table of Contents", section_heading_style))
    story.append(Spacer(1, 0.06 * inch))

    # Default Helvetica has no ₹ (U+20B9) glyph; render rupee figures as "Rs."
    # in the PDF while the JSON/API keeps ₹ for the frontend.
    def _inr_pdf(text: Any) -> str:
        return str(text).replace("₹", "Rs.")

    toc_sections = ["Executive Takeaways"]
    if business_insights and business_insights.get("action_list"):
        action_list_data = business_insights.get("action_list")
        if isinstance(action_list_data, list) and len(action_list_data) > 0:
            toc_sections.append("Priority Action List")
    if business_insights and business_insights.get("enhanced_executive_summary"):
        ees_data = business_insights["enhanced_executive_summary"]
        if isinstance(ees_data, dict) and ees_data.get("narrative"):
            toc_sections.append("Enhanced Executive Summary")
    toc_sections.extend(["Executive Summary", "Analysis Summary", "Key Metrics"])
    if business_insights and business_insights.get("revenue_stability_index"):
        toc_sections.append("Revenue Stability Index")
    if business_insights and business_insights.get("inventory_health_score"):
        toc_sections.append("Inventory Health Score")
        ihs_toc = business_insights.get("inventory_health_score")
        if isinstance(ihs_toc, dict) and ihs_toc.get("dead_stock_count"):
            toc_sections.append("Dead Stock & Slow-Moving Inventory")
    if business_insights and business_insights.get("receivables_risk"):
        rr_toc = business_insights.get("receivables_risk")
        if isinstance(rr_toc, dict) and (rr_toc.get("total_outstanding") or 0) > 0:
            toc_sections.append("Receivables Risk")
    if business_insights and business_insights.get("customer_churn_risk"):
        ccr_toc = business_insights.get("customer_churn_risk")
        if isinstance(ccr_toc, dict) and ccr_toc.get("has_at_risk"):
            toc_sections.append("Customer Churn Risk")
    if business_insights and business_insights.get("early_warning_alerts"):
        ewa_data = business_insights["early_warning_alerts"]
        if isinstance(ewa_data, dict) and ewa_data.get("alert_count", 0) > 0:
            toc_sections.append("Early Warning Alerts")
    if business_insights and business_insights.get("cohort_product_performance"):
        clpp_data = business_insights["cohort_product_performance"]
        if isinstance(clpp_data, dict) and clpp_data.get("cohort_count", 0) > 0:
            toc_sections.append("Product Cohort Performance")
    if business_insights and business_insights.get("customer_segmentation"):
        csca_data = business_insights["customer_segmentation"]
        if isinstance(csca_data, dict) and csca_data.get("segment_count", 0) > 0:
            toc_sections.append("Customer Segmentation")
    if business_insights and business_insights.get("mom_commentary"):
        toc_sections.append("Period Comparison")
    if business_insights and business_insights.get("concentration_risk_dashboard"):
        crd_data = business_insights["concentration_risk_dashboard"]
        if isinstance(crd_data, dict) and crd_data.get("dimension_count", 0) > 0:
            toc_sections.append("Concentration Risk Dashboard")
    if business_insights and business_insights.get("enhanced_products_to_watch"):
        eptw_data = business_insights["enhanced_products_to_watch"]
        if isinstance(eptw_data, dict) and eptw_data.get("product_count", 0) > 0:
            toc_sections.append("Products to Watch (Enhanced)")
    toc_sections.append("Insights")
    if business_insights:
        toc_sections.append("Business Interpretation")
    toc_sections.append("Appendix: Methodology")

    for i, sec in enumerate(toc_sections, 1):
        story.append(Paragraph(f"{i}. &nbsp; {_escape(sec)}", toc_entry_style))

    story.append(Spacer(1, 0.25 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#E5E7EB"), spaceAfter=12, spaceBefore=4))

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
                story.append(HR_MAJOR())
                story.append(Paragraph("Executive Takeaways", major_section_heading_style))
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
    # Priority Action List (distribution niche) — operator to-do list, top of report
    # ------------------------------------------------------------------
    if business_insights and business_insights.get("action_list"):
        try:
            action_list = business_insights.get("action_list")
            if isinstance(action_list, list) and len(action_list) > 0:
                story.append(HR_MAJOR())
                story.append(Paragraph("Priority Action List", major_section_heading_style))
                story.append(Paragraph(
                    "Your top moves this week, in priority order:", small_muted_style
                ))
                story.append(Spacer(1, 0.06 * inch))
                action_bullet_style = ParagraphStyle(
                    "ActionBullet",
                    parent=body_style,
                    leftIndent=10,
                    spaceAfter=2,
                )
                for item in action_list[:6]:
                    if not isinstance(item, dict):
                        continue
                    headline = item.get("headline")
                    if not headline:
                        continue
                    story.append(Paragraph(
                        f"<b>■ {_escape(_inr_pdf(headline))}</b>", action_bullet_style
                    ))
                    detail = item.get("detail")
                    if detail:
                        story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;{_escape(_inr_pdf(detail))}", small_muted_style))
                    story.append(Spacer(1, 0.05 * inch))
                story.append(Spacer(1, 0.2 * inch))
        except Exception:
            pass  # Never fail PDF generation for the action list

    # ------------------------------------------------------------------
    # Enhanced Executive Summary section (if available)
    # ------------------------------------------------------------------
    if business_insights and business_insights.get("enhanced_executive_summary"):
        try:
            ees = business_insights["enhanced_executive_summary"]
            narrative = ees.get("narrative", "")
            if narrative:
                story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#E5E7EB"), spaceAfter=8, spaceBefore=4))
                story.append(Paragraph("Enhanced Executive Summary", section_heading_style))
 
                sentiment = ees.get("overall_sentiment", "neutral")
                confidence = ees.get("confidence", "medium")
                coverage = ees.get("data_coverage", "limited")
                story.append(
                    Paragraph(
                        f"Outlook: <b>{_escape(sentiment.upper())}</b> | "
                        f"Confidence: <b>{_escape(confidence.upper())}</b> | "
                        f"Data coverage: <b>{_escape(coverage.replace('_', ' ').title())}</b>",
                        small_muted_style,
                    )
                )
                story.append(Spacer(1, 0.08 * inch))
 
                story.append(Paragraph(_escape(narrative), body_style))
                story.append(Spacer(1, 0.1 * inch))

                headline_metrics = ees.get("headline_metrics") or []
                if headline_metrics:
                    story.append(Paragraph("<b>Headline Numbers</b>", body_style))
                    for hm in headline_metrics[:4]:
                        story.append(Paragraph(f"▸ {_escape(_inr_pdf(str(hm)))}", small_muted_style))
                    story.append(Spacer(1, 0.08 * inch))

                key_positives = ees.get("key_positives") or []
                if key_positives:
                    story.append(Paragraph("<b>Key Strengths</b>", body_style))
                    for p in key_positives[:4]:
                        story.append(Paragraph(f"\u2714 {_escape(str(p))}", small_muted_style))
                    story.append(Spacer(1, 0.08 * inch))
 
                key_risks = ees.get("key_risks") or []
                if key_risks:
                    story.append(Paragraph("<b>Key Risks</b>", body_style))
                    for r in key_risks[:4]:
                        story.append(Paragraph(f"\u26a0 {_escape(str(r))}", small_muted_style))
                    story.append(Spacer(1, 0.08 * inch))
 
                watchpoints = ees.get("watchpoints") or []
                if watchpoints:
                    story.append(Paragraph("<b>Leadership Watchpoints</b>", body_style))
                    for w in watchpoints[:4]:
                        story.append(Paragraph(f"\u25b6 {_escape(str(w))}", small_muted_style))
                    story.append(Spacer(1, 0.08 * inch))
 
                ees_warning = ees.get("warning")
                if ees_warning:
                    story.append(Paragraph(f"\u26a0 {_escape(str(ees_warning))}", small_muted_style))
 
                story.append(Spacer(1, 0.15 * inch))
        except Exception:
            pass  # Never fail PDF generation for EES


    # ------------------------------------------------------------------
    # Executive Summary section (always)
    # ------------------------------------------------------------------
    story.append(HR_STANDARD())
    story.append(Paragraph("Executive Summary", section_heading_style))
    exec_paragraph = _build_executive_paragraph(report, business_insights)
    story.append(Paragraph(_escape(exec_paragraph), body_style))
    story.append(Spacer(1, 0.15 * inch))

    story.append(HR_STANDARD())
    story.append(Paragraph("Analysis Summary", section_heading_style))
    revenue_delta = None
    for d in (report.metric_deltas or []):
        if (d.name or "").lower() == "revenue":
            revenue_delta = d
            break
    total_revenue_value = revenue_delta.current if revenue_delta else None
    
    # Total transactions — use direct field, not regex extraction
    total_transactions_value = report.total_transactions
    
    # Products analyzed — use direct field
    products_analyzed_value = report.products_analyzed
    
    insights_generated_value = len(report.insights or [])

    # 2-column table for metrics
    summary_cells = [
        [
            Paragraph("Total Revenue", label_style),
            Paragraph("Total Transactions", label_style)
        ],
        [
            Paragraph(f"${total_revenue_value:,.2f}" if total_revenue_value is not None else "\u2014", metric_value_style),
            Paragraph(f"{total_transactions_value:,d}" if total_transactions_value is not None else "\u2014", metric_value_style)
        ],
        [
            Paragraph("Products Analyzed", label_style),
            Paragraph("Insights Generated", label_style)
        ],
        [
            Paragraph(f"{products_analyzed_value:,d}" if products_analyzed_value is not None else "\u2014", metric_value_style),
            Paragraph(f"{insights_generated_value:,d}", metric_value_style)
        ]
    ]

    summary_table = Table(summary_cells, colWidths=[doc.width/2.0, doc.width/2.0])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), HexColor("#F9FAFB")),
        ('BACKGROUND', (0, 2), (1, 2), HexColor("#F9FAFB")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 1), (1, 1), 0.5, HexColor("#F3F4F6")),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.25 * inch))

    # ------------------------------------------------------------------
    # MoM Commentary section (if available)
    # ------------------------------------------------------------------
    if business_insights and business_insights.get("mom_commentary"):
        try:
            mom = business_insights["mom_commentary"]
            story.append(HR_STANDARD())
            story.append(Paragraph("Period Comparison", section_heading_style))
            
            direction = mom.get("direction", "no_baseline")
            magnitude = mom.get("magnitude", "no_baseline")
            meaningful = mom.get("is_meaningful", False)
            
            badge_text = f"<b>{direction.upper()}</b>"
            if magnitude != "no_baseline":
                badge_text += f" | <b>{magnitude.upper()}</b>"
            if meaningful:
                badge_text += " | <b>MEANINGFUL</b>"
            
            story.append(Paragraph(badge_text, small_muted_style))
            story.append(Spacer(1, 0.05 * inch))
            
            rev_curr = mom.get("revenue_current", 0)
            rev_base = mom.get("revenue_baseline")
            abs_chg = mom.get("absolute_change")
            pct_chg = mom.get("percent_change")
            
            metrics_line = f"Current Period: ${rev_curr:,.2f}"
            if rev_base is not None:
                metrics_line += f" | Baseline: ${rev_base:,.2f}"
            if pct_chg is not None:
                sign = "+" if pct_chg >= 0 else ""
                metrics_line += f" | Change: {sign}{pct_chg:.1f}% (${abs_chg:,.2f})"
                
            story.append(Paragraph(metrics_line, body_style))
            story.append(Spacer(1, 0.1 * inch))
            
            commentary = mom.get("commentary", "")
            if commentary:
                story.append(Paragraph(_escape(commentary), body_style))
                story.append(Spacer(1, 0.1 * inch))
                
            interpretation = mom.get("interpretation", "")
            if interpretation:
                story.append(Paragraph(f"<b>Interpretation:</b> {_escape(interpretation)}", small_muted_style))
            
            warning = mom.get("warning")
            if warning:
                story.append(Paragraph(f"\u26a0 {_escape(str(warning))}", small_muted_style))
                
            conf = mom.get("confidence", "medium")
            n = mom.get("sample_size", 0)
            story.append(Paragraph(f"Confidence: {conf.upper()} (n={n:,})", small_muted_style))
            
            story.append(Spacer(1, 0.25 * inch))
        except Exception:
            pass

    # C5. DATA QUALITY SUMMARY IN PDF
    if business_insights and business_insights.get("data_quality"):
        dq = business_insights["data_quality"]
        story.append(HR_STANDARD())
        story.append(Paragraph("Data Quality Summary", section_heading_style))
        dq_bullets = []
        if dq.get("rows_before") is not None and dq.get("rows_after") is not None:
            dq_bullets.append(f"• Rows after cleaning: {dq['rows_after']:,} (from {dq['rows_before']:,})")
        
        if dq.get("duplicate_rows_dropped"):
            dq_bullets.append(f"• Duplicate rows removed: {dq['duplicate_rows_dropped']:,}")
        
        if dq.get("null_rows_dropped"):
            dq_bullets.append(f"• Null rows removed: {dq['null_rows_dropped']:,}")
            
        # New: Schema detection
        schema = dq.get("schema_detected")
        if schema:
            detected = schema.get("detected_columns", {})
            if detected:
                fields_found = ", ".join(sorted(detected.keys()))
                dq_bullets.append(f"• Schema fields detected: {_escape(fields_found)}")
        
        # New: Granularity
        gran = dq.get("granularity")
        if gran and gran.get("granularity") != "unknown":
            dq_bullets.append(f"• Data granularity: {_escape(gran['granularity'].replace('_', ' ').title())}")
        
        # New: Dates
        date_cols = dq.get("date_columns_parsed")
        if date_cols:
            dq_bullets.append(f"• Date columns parsed: {', '.join(date_cols)}")

        if dq.get("columns_renamed"):
            dq_bullets.append(f"• Columns canonicalized: {', '.join(dq['columns_renamed'])}")
            
        for b in dq_bullets:
            story.append(Paragraph(b, body_style))
            
        # New: Warnings
        warnings = dq.get("warnings")
        if warnings:
            story.append(Spacer(1, 0.05 * inch))
            for w in warnings[:5]:
                story.append(Paragraph(f"\u26a0 {_escape(str(w))}", small_muted_style))
                
        story.append(Spacer(1, 0.2 * inch))

    # ------------------------------------------------------------------
    # Key Metrics section
    # ------------------------------------------------------------------
    story.append(HR_STANDARD())
    story.append(Paragraph("Key Metrics", section_heading_style))

    if report.metric_deltas:
        metric_rows = []
        for i, m in enumerate(report.metric_deltas):
            if m.baseline == 0:
                val_text = f"${m.current:,.2f}"
                comp_text = "N/A (No Baseline)"
            else:
                sign = "+" if m.percent_change >= 0 else ""
                val_text = f"${m.current:,.2f}"
                comp_text = f"{sign}{m.percent_change:.1f}% vs ${m.baseline:,.2f}"
            
            metric_rows.append([
                Paragraph(m.name.title(), body_style),
                Paragraph(val_text, metric_value_style),
                Paragraph(comp_text, small_muted_style)
            ])

        metrics_table = Table(metric_rows, colWidths=[doc.width*0.3, doc.width*0.25, doc.width*0.45])
        metrics_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -1), 0.25, HexColor("#EEEEEE")),
        ]))
        story.append(metrics_table)
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
            # ... (rest stays the same)
            story.append(HR_STANDARD())
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
            # ...
            story.append(HR_STANDARD())
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
    # Dead Stock & Slow-Moving Inventory section (distribution niche)
    # ------------------------------------------------------------------
    if business_insights and business_insights.get("inventory_health_score"):
        try:
            ihs_ds = business_insights["inventory_health_score"]
            dead_skus = ihs_ds.get("dead_stock_skus") if isinstance(ihs_ds, dict) else None
            dead_count = ihs_ds.get("dead_stock_count") if isinstance(ihs_ds, dict) else None
            dead_value = ihs_ds.get("total_dead_stock_value") if isinstance(ihs_ds, dict) else None
            dead_window = ihs_ds.get("dead_stock_window_days") if isinstance(ihs_ds, dict) else 60
            if dead_count:
                story.append(HR_STANDARD())
                story.append(Paragraph("Dead Stock & Slow-Moving Inventory", section_heading_style))
                if dead_value is not None:
                    story.append(Paragraph(
                        f"<b>{_inr_pdf(_format_inr_lakh(dead_value))}</b> of capital is tied up in "
                        f"<b>{dead_count}</b> SKU(s) with no transaction in {dead_window}+ days.",
                        body_style,
                    ))
                else:
                    story.append(Paragraph(
                        f"<b>{dead_count}</b> SKU(s) had no transaction in {dead_window}+ days.",
                        body_style,
                    ))
                story.append(Spacer(1, 0.05 * inch))
                for s in (dead_skus or [])[:10]:
                    if not isinstance(s, dict):
                        continue
                    sku = s.get("sku", "")
                    val = s.get("value_tied_up")
                    days = s.get("days_inactive")
                    line = f"• {_escape(str(sku))}"
                    if val:
                        line += f" — {_inr_pdf(_format_inr(val))} tied up"
                    if days is not None:
                        line += f", idle {days} days"
                    story.append(Paragraph(line, small_muted_style))
                story.append(Spacer(1, 0.25 * inch))
        except Exception:
            pass  # Never fail PDF generation for dead stock

    # ------------------------------------------------------------------
    # Receivables Risk section (distribution niche)
    # ------------------------------------------------------------------
    if business_insights and business_insights.get("receivables_risk"):
        try:
            rr = business_insights["receivables_risk"]
            if isinstance(rr, dict) and (rr.get("total_outstanding") or 0) > 0:
                story.append(HR_STANDARD())
                story.append(Paragraph("Receivables Risk", section_heading_style))
                total = rr.get("total_outstanding")
                cust_n = rr.get("customer_count")
                headline = f"<b>{_inr_pdf(_format_inr_lakh(total))}</b> outstanding across <b>{cust_n}</b> customer(s)."
                if rr.get("aging_available") and (rr.get("over_45_amount") or 0) > 0:
                    headline += (
                        f" {_inr_pdf(_format_inr_lakh(rr.get('over_45_amount')))} is over 45 days old"
                    )
                    if rr.get("over_90_amount"):
                        headline += f" ({_inr_pdf(_format_inr_lakh(rr.get('over_90_amount')))} over 90 days)"
                    headline += "."
                story.append(Paragraph(headline, body_style))
                story.append(Spacer(1, 0.05 * inch))
                for c in (rr.get("customers") or [])[:10]:
                    if not isinstance(c, dict):
                        continue
                    name = c.get("customer", "")
                    amt = c.get("outstanding")
                    bucket = c.get("aging_bucket")
                    line = f"• {_escape(str(name))} — {_inr_pdf(_format_inr(amt))}"
                    if bucket:
                        line += f" ({_escape(str(bucket))} days)"
                    story.append(Paragraph(line, small_muted_style))
                rr_warning = rr.get("warning")
                if rr_warning:
                    story.append(Paragraph(f"⚠ {_escape(str(rr_warning))}", small_muted_style))
                story.append(Spacer(1, 0.25 * inch))
        except Exception:
            pass  # Never fail PDF generation for receivables

    # ------------------------------------------------------------------
    # Customer Churn Risk section (distribution niche)
    # ------------------------------------------------------------------
    if business_insights and business_insights.get("customer_churn_risk"):
        try:
            ccr = business_insights["customer_churn_risk"]
            if isinstance(ccr, dict) and ccr.get("has_at_risk"):
                story.append(HR_STANDARD())
                story.append(Paragraph("Customer Churn Risk", section_heading_style))
                flagged = (ccr.get("at_risk_count") or 0) + (ccr.get("churned_count") or 0)
                rev_at_risk = ccr.get("revenue_at_risk")
                headline = f"<b>{flagged}</b> shop(s) have gone quiet"
                if rev_at_risk:
                    headline += f", with <b>{_inr_pdf(_format_inr_lakh(rev_at_risk))}</b> of historic revenue at risk"
                headline += ". Following up with these customers is likely to recover revenue."
                story.append(Paragraph(headline, body_style))
                story.append(Spacer(1, 0.05 * inch))
                for c in (ccr.get("customers") or [])[:10]:
                    if not isinstance(c, dict):
                        continue
                    if c.get("risk") not in ("churned", "at_risk"):
                        continue
                    name = c.get("customer", "")
                    rev = c.get("total_revenue")
                    days = c.get("days_since_last_order")
                    risk = c.get("risk", "")
                    line = f"• {_escape(str(name))} — {_escape(str(risk).replace('_', ' '))}"
                    if rev:
                        line += f", {_inr_pdf(_format_inr(rev))} historic"
                    if days is not None:
                        line += f", quiet {days} days"
                    story.append(Paragraph(line, small_muted_style))
                story.append(Spacer(1, 0.25 * inch))
        except Exception:
            pass  # Never fail PDF generation for churn

    # ------------------------------------------------------------------
    # Early Warning Alerts section (if available and non-empty)
    # ------------------------------------------------------------------
    if business_insights and business_insights.get("early_warning_alerts"):
        try:
            ewa = business_insights["early_warning_alerts"]
            ewa_alerts = ewa.get("alerts") or []
            if ewa_alerts:
                story.append(HR_STANDARD())
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
                story.append(HR_STANDARD())
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
    # Customer Segmentation section (if available and non-empty)
    # ------------------------------------------------------------------
    if business_insights and business_insights.get("customer_segmentation"):
        try:
            csca = business_insights["customer_segmentation"]
            csca_segments = csca.get("segments") or []
            if csca_segments:
                story.append(HR_STANDARD())
                story.append(Paragraph("Customer Segmentation", section_heading_style))
 
                csca_basis = csca.get("segment_basis", "")
                total_cust = csca.get("total_customers", 0)
                if csca_basis:
                    story.append(
                        Paragraph(
                            f"Segmentation method: <b>{_escape(csca_basis.upper())}</b> | "
                            f"Total customers: <b>{total_cust:,}</b> | "
                            f"Segments: <b>{len(csca_segments)}</b>",
                            small_muted_style,
                        )
                    )
                    story.append(Spacer(1, 0.1 * inch))
 
                tier_icon = {
                    "high_value": "\u2605",
                    "growing": "\u25b2",
                    "stable_value": "\u25cf",
                    "at_risk": "\u26a0",
                    "declining": "\u25bc",
                    "insufficient_data": "\u2014",
                }
 
                for seg in csca_segments:
                    label = seg.get("segment_label", "")
                    tier = seg.get("tier", "")
                    icon = tier_icon.get(tier, "")
                    rev_share = seg.get("revenue_share_pct", 0)
                    cust_count = seg.get("customer_count", 0)
                    growth = seg.get("period_growth_pct")
                    explanation = seg.get("explanation", "")
                    confidence = seg.get("confidence", "")
                    warning = seg.get("warning")
                    avg_freq = seg.get("avg_order_frequency")
                    avg_rec = seg.get("avg_recency_days")
 
                    tier_display = tier.replace("_", " ").title()
                    growth_str = f"{growth:+.1f}%" if growth is not None else "N/A"
 
                    story.append(
                        Paragraph(
                            f"{icon} <b>{_escape(str(label))}</b> — {_escape(tier_display)}",
                            body_style,
                        )
                    )
                    metrics_parts = [
                        f"{cust_count:,} customers",
                        f"Rev share: {rev_share:.1f}%",
                        f"Growth: {growth_str}",
                    ]
                    if avg_freq is not None:
                        metrics_parts.append(f"Avg freq: {avg_freq:.1f}")
                    if avg_rec is not None:
                        metrics_parts.append(f"Recency: {avg_rec:.0f}d")
                    metrics_parts.append(f"Confidence: {str(confidence).upper()}")
                    story.append(
                        Paragraph(
                            " | ".join(metrics_parts),
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
            pass  # Never fail PDF generation for CSCA
 
    # ------------------------------------------------------------------
    # Concentration Risk Dashboard section (if available and non-empty)
    # ------------------------------------------------------------------
    if business_insights and business_insights.get("concentration_risk_dashboard"):
        try:
            crd = business_insights["concentration_risk_dashboard"]
            crd_dims = crd.get("dimensions") or []
            if crd_dims:
                story.append(HR_STANDARD())
                story.append(Paragraph("Concentration Risk Dashboard", section_heading_style))
 
                overall_risk = crd.get("overall_risk", "low")
                overall_score = crd.get("overall_score", 0)
                story.append(
                    Paragraph(
                        f"Overall risk: <b>{_escape(overall_risk.upper())}</b> "
                        f"(score: {overall_score:.1f}/100) | "
                        f"Dimensions analyzed: <b>{len(crd_dims)}</b>",
                        small_muted_style,
                    )
                )
                story.append(Spacer(1, 0.1 * inch))
 
                risk_icon = {
                    "critical": "\u26d4",
                    "high": "\u26a0",
                    "moderate": "\u25b2",
                    "low": "\u2714",
                }
 
                for dim in crd_dims:
                    dim_name = dim.get("dimension", "")
                    risk = dim.get("risk_level", "low")
                    icon = risk_icon.get(risk, "")
                    score = dim.get("composite_score", 0)
                    hhi = dim.get("hhi", 0)
                    gini = dim.get("gini", 0)
                    top_1 = dim.get("top_1_share_pct", 0)
                    top_5 = dim.get("top_5_share_pct", 0)
                    explanation = dim.get("explanation", "")
                    confidence = dim.get("confidence", "")
                    warning = dim.get("warning")
                    trend = dim.get("trend")
                    contributors = dim.get("top_contributors") or []
 
                    story.append(
                        Paragraph(
                            f"{icon} <b>{_escape(dim_name.capitalize())} Concentration</b> "
                            f"— {_escape(risk.upper())} (score: {score:.1f})",
                            body_style,
                        )
                    )
                    metrics_line = (
                        f"HHI: {hhi:.0f} | Gini: {gini:.2f} | "
                        f"Top 1: {top_1:.1f}% | Top 5: {top_5:.1f}%"
                    )
                    if trend:
                        metrics_line += f" | Trend: {trend}"
                    metrics_line += f" | Confidence: {str(confidence).upper()}"
                    story.append(Paragraph(metrics_line, small_muted_style))
 
                    if explanation:
                        story.append(Paragraph(_escape(str(explanation)), small_muted_style))
 
                    if contributors:
                        contrib_names = [f"{c.get('name', '')} ({c.get('share_pct', 0):.1f}%)" for c in contributors[:3]]
                        story.append(
                            Paragraph(
                                f"Top contributors: {', '.join(contrib_names)}",
                                small_muted_style,
                            )
                        )
 
                    if warning:
                        story.append(Paragraph(f"\u26a0 {_escape(str(warning))}", small_muted_style))
                    story.append(Spacer(1, 0.12 * inch))
 
                story.append(Spacer(1, 0.1 * inch))
        except Exception:
            pass  # Never fail PDF generation for CRD
 
    # ------------------------------------------------------------------
    # Enhanced Products to Watch section (if available)
    # ------------------------------------------------------------------
    if business_insights and business_insights.get("enhanced_products_to_watch"):
        try:
            eptw = business_insights["enhanced_products_to_watch"]
            prods = eptw.get("products") or []
            if prods:
                story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#E5E7EB"), spaceAfter=8, spaceBefore=4))
                
                header_text = "Products to Watch (Enhanced)"
                if eptw.get("has_declining"):
                    header_text += " — <b>DECLINING DETECTED</b>"
                
                story.append(Paragraph(header_text, section_heading_style))
                
                status_icon = {
                    "declining": "\u25bc",
                    "unstable": "\u2248",
                    "watch": "\u25cf",
                    "improving": "\u25b2",
                    "low_confidence": "!",
                }
                
                for p in prods:
                    name = p.get("product", "Unknown")
                    status = p.get("status", "watch")
                    reason = p.get("reason", "")
                    share = p.get("revenue_share_pct", 0)
                    trend = p.get("trend_direction", "")
                    action = p.get("action_direction", "")
                    icon = status_icon.get(status, "\u25cf")
                    
                    story.append(Paragraph(f"{icon} <b>{_escape(name)}</b> — {status.upper()}", body_style))
                    
                    details = f"Share: {share:.1f}%"
                    if trend and trend != "insufficient_data":
                        details += f" | Trend: {trend.upper()}"
                    details += f" | Confidence: {p.get('confidence', 'medium').upper()}"
                    
                    story.append(Paragraph(details, small_muted_style))
                    story.append(Paragraph(f"<i>Reason:</i> {_escape(reason)}", small_muted_style))
                    if action:
                        story.append(Paragraph(f"<i>Action:</i> {_escape(action)}", small_muted_style))
                    story.append(Spacer(1, 0.12 * inch))
                
                eptw_warning = eptw.get("warning")
                if eptw_warning:
                    story.append(Paragraph(f"\u26a0 {_escape(str(eptw_warning))}", small_muted_style))
                    
                story.append(Spacer(1, 0.15 * inch))
        except Exception:
            pass

 
    # ------------------------------------------------------------------
    # Insights section
    # ------------------------------------------------------------------
    story.append(HR_MAJOR())
    story.append(Paragraph("Insights", major_section_heading_style))

    if report.insights:
        any_negative_insight = False
        for ins in report.insights:
            importance = _importance_label(ins.severity)
            sev_prefix = f"[{ins.severity.upper()}] " if ins.severity else ""

            story.append(Paragraph(f"<b>{sev_prefix}{_escape(ins.title)}</b>", body_style))
            story.append(Paragraph(f"<b>Why it matters:</b> {_escape(importance)}", small_muted_style))

            if getattr(ins, "code", "") == "REVENUE_VOLATILITY":
                desc = (
                    "Revenue swings dramatically across transactions — the gap between typical orders and peak orders is extreme, "
                    "making the average transaction value unreliable as a planning number."
                )
            else:
                desc = _rewrite_stat_language(ins.description)
            story.append(Paragraph(_escape(desc), body_style))

            # Render enrichment fields if present
            fallback_context = ""
            if getattr(ins, "affected_metric", None):
                fallback_context = f"Focus on the drivers behind {ins.affected_metric} first — it is the fastest way to reduce operational uncertainty."

            driver_plain = _rewrite_driver_plain_english(ins.driver or "", title=ins.title)
            implication = _ensure_implication(ins.implication, fallback_context)
            action = _rewrite_action_directional(
                ins.action_direction,
                title=ins.title or "",
                description=ins.description or "",
                driver=ins.driver or "",
                context=fallback_context,
            )

            if driver_plain:
                story.append(Paragraph(f"<b>Driver:</b> {_escape(driver_plain)}", small_muted_style))
            
            story.append(Paragraph(f"<b>Implication:</b> {_escape(implication)}", small_muted_style))
            story.append(Paragraph(f"<b>Action:</b> {_escape(action)}", small_muted_style))

            if _contains_negative_revenue(ins.title, ins.description, ins.driver or "", ins.implication or ""):
                any_negative_insight = True
                story.append(Paragraph(_escape(_negative_revenue_note()), small_muted_style))

            if ins.confidence:
                conf_text = f"Confidence: {_format_confidence(ins.confidence, getattr(ins, 'confidence_basis', None))}"
                story.append(Paragraph(conf_text, small_muted_style))

            story.append(HR_MINOR())
            story.append(Spacer(1, 0.1 * inch))

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
            story.append(Spacer(1, 0.1 * inch))
            story.append(HR_MAJOR())
            story.append(Paragraph("Business Interpretation", major_section_heading_style))
            story.append(Spacer(1, 0.05 * inch))

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
    story.append(HR_MAJOR())
    story.append(Paragraph("Appendix: Methodology & Disclaimers", major_section_heading_style))

    appendix_items = [
        ("Revenue Detection", "Semantic column matching across synonyms (sales, turnover, gmv) with fuzzy confidence thresholds."),
        ("Concentration Risk", "Computed using HHI and Gini coefficients applied to transaction-level revenue distribution."),
        ("Stability Index", "Weighted metric of coefficient of variation (CV) and period-over-period volatility."),
        ("Product Cohorts", "Dynamic grouping by revenue contribution tiers using Z-score outlier detection."),
        ("Data Quality", "Automated currency canonicalization, handle missing value imputation, and duplicate detection."),
    ]
    
    for title, desc in appendix_items:
        story.append(Paragraph(f"<b>{title}:</b> {desc}", small_muted_style))
        story.append(Spacer(1, 0.05 * inch))

    disclaimer = (
        "This report is generated for internal business advisory purposes. Figures reflect the dataset "
        "provided as-is; results are directional indicators and not audited financial statements. "
        "Confidence scores indicate statistical robustness, not factual certainty."
    )
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(disclaimer, confidential_style))
    story.append(Spacer(1, 0.2 * inch))

    # Build PDF (IO + layout only; no contract changes)
    doc.build(story, canvasmaker=PageNumCanvas)
