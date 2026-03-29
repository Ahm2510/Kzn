from datetime import datetime
from typing import Optional, Dict, Any
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.colors import HexColor

from app.schemas.insight.report import InsightReport


_CURRENCY_NEGATIVE_RE = re.compile(r"\$\s*-\s*\d")
_CV_RE = re.compile(r"\bCV\s*[:=]\s*(\d+(?:\.\d+)?)\b", flags=re.IGNORECASE)
_COEFF_VAR_RE = re.compile(
    r"\bcoefficient\s+of\s+variation\b", flags=re.IGNORECASE
)
_N_RE = re.compile(r"\bn\s*[:=]\s*(\d+)\b", flags=re.IGNORECASE)


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

    # Remove raw sample-size callouts from the main narrative.
    out = _N_RE.sub("", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    out = out.replace("()", "").strip()
    return out


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

    date_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    story.append(Paragraph(f"Generated on {date_str}", date_style))
    story.append(Spacer(1, 0.35 * inch))

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
                story.append(Paragraph("Executive Takeaways", section_heading_style))
                bullet_style = ParagraphStyle(
                    "ExecBullet",
                    parent=body_style,
                    leftIndent=10,
                )
                for bullet in executive_takeaways[:6]:
                    if bullet:
                        story.append(Paragraph(f"• {bullet}", bullet_style))
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
    story.append(Paragraph("Executive Summary", section_heading_style))
    exec_paragraph = _build_executive_paragraph(report, business_insights)
    story.append(Paragraph(_escape(exec_paragraph), body_style))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Analysis Summary", section_heading_style))
    story.append(Paragraph(_escape(_rewrite_stat_language(report.summary)), body_style))
    story.append(Spacer(1, 0.25 * inch))

    # ------------------------------------------------------------------
    # Key Metrics section
    # ------------------------------------------------------------------
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
    # Insights section
    # ------------------------------------------------------------------
    story.append(Paragraph("Insights", section_heading_style))

    insights_style = body_style

    if report.insights:
        any_negative_insight = False
        for ins in report.insights:
            importance = _importance_label(ins.severity)

            title_line = f"<b>{_escape(ins.title)}</b>"
            story.append(Paragraph(title_line, insights_style))
            story.append(Paragraph(f"<i>Why it matters:</i> {_escape(importance)}", small_muted_style))

            desc = _rewrite_stat_language(ins.description)
            story.append(Paragraph(_escape(desc), insights_style))

            # Render enrichment fields if present
            fallback_context = ""
            if getattr(ins, "affected_metric", None):
                fallback_context = f"Focus on the drivers behind {ins.affected_metric} first — it is the fastest way to reduce operational uncertainty."

            driver = _rewrite_stat_language(ins.driver or "")
            implication = _ensure_implication(ins.implication, fallback_context)
            action = _ensure_action(
                ins.action_direction,
                "Identify the top 10% of transactions driving the largest share of revenue. Determine whether they are repeat customers, specific products, or seasonal spikes — that answer dictates whether you prioritize retention, availability/pricing, or seasonal planning.",
            )

            if driver:
                story.append(Paragraph(f"<i>Driver:</i> {_escape(driver)}", small_muted_style))
            story.append(Paragraph(f"<i>Implication:</i> {_escape(implication)}", small_muted_style))
            story.append(Paragraph(f"<i>Action:</i> {_escape(action)}", small_muted_style))

            if _contains_negative_revenue(ins.title, ins.description, ins.driver or "", ins.implication or ""):
                any_negative_insight = True
                story.append(Paragraph(_escape(_negative_revenue_note()), small_muted_style))

            if ins.confidence:
                conf_text = f"Confidence: {ins.confidence}"
                if ins.confidence_basis:
                    # Keep basis, but avoid raw statistical language dominating the report.
                    conf_text += f" ({_escape(_rewrite_stat_language(ins.confidence_basis))})"
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
            story.append(Paragraph("Business Interpretation", section_heading_style))
            story.append(Spacer(1, 0.1 * inch))

            detail_style = body_style

            small_style = small_muted_style

            def render_enriched_insight(name: str, insight: dict) -> None:
                if not insight:
                    return
                story.append(Paragraph(f"<b>{name}</b>", detail_style))

                if insight.get("description"):
                    story.append(Paragraph(_escape(_rewrite_stat_language(insight["description"])) , detail_style))

                if insight.get("driver"):
                    story.append(
                        Paragraph(
                            f"<i>Driver:</i> {_escape(_rewrite_stat_language(insight['driver']))}",
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
                    story.append(
                        Paragraph(
                            f"<i>Action:</i> {_escape(_rewrite_stat_language(insight['action_direction']))}",
                            detail_style,
                        )
                    )

                confidence = insight.get("confidence")
                confidence_basis = insight.get("confidence_basis")
                if confidence:
                    conf_text = f"Confidence: {confidence}"
                    if confidence_basis:
                        conf_text += f" ({confidence_basis})"
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

            exec_summary = business_insights.get("executive_summary")
            if exec_summary:
                story.append(Spacer(1, 0.1 * inch))
                story.append(Paragraph("Additional Notes", section_heading_style))
                story.append(Paragraph(_escape(_rewrite_stat_language(exec_summary)), detail_style))
        except Exception:
            # Defensive - never fail PDF generation for business insights
            pass

    # Build PDF (IO + layout only; no contract changes)
    doc.build(story)
