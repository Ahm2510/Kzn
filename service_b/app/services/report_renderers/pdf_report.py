from datetime import datetime
from typing import Optional, Dict, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.colors import HexColor

from app.schemas.insight.report import InsightReport


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
    # Summary section
    # ------------------------------------------------------------------
    story.append(Paragraph("Summary", section_heading_style))
    story.append(Paragraph(report.summary, body_style))
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
    else:
        story.append(Paragraph("<i>No metrics available.</i>", metrics_style))

    story.append(Spacer(1, 0.25 * inch))

    # ------------------------------------------------------------------
    # Insights section
    # ------------------------------------------------------------------
    story.append(Paragraph("Insights", section_heading_style))

    insights_style = body_style

    if report.insights:
        for ins in report.insights:
            severity_color = {
                "high": "#CC0000",
                "medium": "#FF9900",
                "low": "#0066CC",
            }.get(ins.severity.lower(), "#666666")

            insight_text = (
                f"<b>[<font color='{severity_color}'>{ins.severity.upper()}</font>]</b> "
                f"<b>{ins.title}</b><br/>"
                f"{ins.description}"
            )
            story.append(Paragraph(insight_text, insights_style))

            # Render enrichment fields if present
            if ins.driver:
                story.append(Paragraph(f"<i>Driver:</i> {ins.driver}", small_muted_style))
            if ins.implication:
                story.append(Paragraph(f"<i>Implication:</i> {ins.implication}", small_muted_style))
            if ins.action_direction:
                story.append(Paragraph(f"<i>Action:</i> {ins.action_direction}", small_muted_style))
            if ins.confidence:
                conf_text = f"Confidence: {ins.confidence}"
                if ins.confidence_basis:
                    conf_text += f" ({ins.confidence_basis})"
                story.append(Paragraph(conf_text, small_muted_style))

            story.append(Spacer(1, 0.18 * inch))
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
                    story.append(Paragraph(insight["description"], detail_style))

                if insight.get("driver"):
                    story.append(
                        Paragraph(f"<i>Driver:</i> {insight['driver']}", detail_style)
                    )

                if insight.get("implication"):
                    story.append(
                        Paragraph(
                            f"<i>Implication:</i> {insight['implication']}", detail_style
                        )
                    )

                if insight.get("action_direction"):
                    story.append(
                        Paragraph(
                            f"<i>Action:</i> {insight['action_direction']}", detail_style
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
                story.append(Paragraph("Executive Summary", section_heading_style))
                story.append(Paragraph(exec_summary, detail_style))
        except Exception:
            # Defensive - never fail PDF generation for business insights
            pass

    # Build PDF (IO + layout only; no contract changes)
    doc.build(story)
