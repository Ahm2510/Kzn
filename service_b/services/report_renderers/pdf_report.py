from datetime import datetime
from typing import Optional, Dict, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.colors import HexColor

from schemas.insight.report import InsightReport


def render_pdf(
    report: InsightReport,
    output_path: str,
    business_insights: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Render a professional executive PDF report from an InsightReport.
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
    # Professional Typography Styles
    # ------------------------------------------------------------------
    TitleStyle = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=26,
        leading=30,
        spaceAfter=8,
        textColor=HexColor("#1a1a1a"),
        fontName="Helvetica-Bold",
    )

    SubtitleStyle = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        spaceAfter=4,
        textColor=HexColor("#666666"),
        fontName="Helvetica",
    )

    HeadingStyle = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=16,
        leading=20,
        spaceBefore=18,
        spaceAfter=10,
        textColor=HexColor("#333333"),
        fontName="Helvetica-Bold",
    )

    SubheadingStyle = ParagraphStyle(
        "Subheading",
        parent=styles["Heading3"],
        fontSize=13,
        leading=16,
        spaceBefore=12,
        spaceAfter=6,
        textColor=HexColor("#374151"),
        fontName="Helvetica-Bold",
    )

    BodyStyle = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=11,
        leading=15,
        spaceAfter=8,
        textColor=HexColor("#4a4a4a"),
        fontName="Helvetica",
    )

    SummaryStyle = ParagraphStyle(
        "Summary",
        parent=styles["Normal"],
        fontSize=12,
        leading=18,
        spaceAfter=12,
        textColor=HexColor("#1a1a1a"),
        fontName="Helvetica",
    )

    MutedTextStyle = ParagraphStyle(
        "MutedText",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        textColor=HexColor("#6b7280"),
        fontName="Helvetica-Oblique",
    )

    # Legacy compatibility mappings
    title_style = TitleStyle
    subtitle_style = SubtitleStyle
    section_heading_style = HeadingStyle
    body_style = BodyStyle
    small_muted_style = MutedTextStyle

    # ------------------------------------------------------------------
    # Section 1 — Header
    # ------------------------------------------------------------------
    story.append(Paragraph("Business Insight Report", title_style))
    story.append(Paragraph("Generated for revenue analysis", subtitle_style))

    current_time = datetime.now()
    date_str = current_time.strftime("%B %d, %Y at %I:%M %p")
    story.append(Paragraph(f"Generated on {date_str}", MutedTextStyle))
    story.append(Spacer(1, 0.24 * inch))
    story.append(HRFlowable(width="100%", color=HexColor("#e5e7eb")))
    story.append(Spacer(1, 0.18 * inch))

    # ------------------------------------------------------------------
    # Section 2 — Executive Takeaways (if business_insights present)
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
                    leading=16,
                )
                for bullet in executive_takeaways[:6]:
                    if bullet:
                        story.append(Paragraph(f"• {bullet}", bullet_style))
                        story.append(Spacer(1, 0.12 * inch))
                story.append(Spacer(1, 0.24 * inch))
                story.append(HRFlowable(width="100%", color=HexColor("#e5e7eb")))
                story.append(Spacer(1, 0.18 * inch))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Section 3 — Summary
    # ------------------------------------------------------------------
    story.append(Paragraph("Summary", section_heading_style))
    story.append(Paragraph(report.summary, SummaryStyle))
    story.append(Spacer(1, 0.24 * inch))
    story.append(HRFlowable(width="100%", color=HexColor("#e5e7eb")))
    story.append(Spacer(1, 0.18 * inch))

    # ------------------------------------------------------------------
    # Section 4 — Analysis Scope (static text)
    # ------------------------------------------------------------------
    story.append(Paragraph("Analysis Scope", section_heading_style))
    story.append(Paragraph("<b>Analyzed</b>", SubheadingStyle))
    story.append(Paragraph("• Revenue performance<br/>• Revenue distribution patterns<br/>• Stability indicators", body_style))
    story.append(Spacer(1, 0.12 * inch))
    story.append(Paragraph("<b>Not analyzed</b>", SubheadingStyle))
    story.append(Paragraph("• Costs<br/>• Profit margins<br/>• Forecasting<br/>• Customer segmentation", body_style))
    story.append(Spacer(1, 0.24 * inch))
    story.append(HRFlowable(width="100%", color=HexColor("#e5e7eb")))
    story.append(Spacer(1, 0.18 * inch))

    # ------------------------------------------------------------------
    # Section 5 — Key Metrics
    # ------------------------------------------------------------------
    story.append(Paragraph("Key Metrics", HeadingStyle))

    if report.metric_deltas:
        try:
            rows = []
            has_baseline = any(getattr(m, "baseline", 0) and getattr(m, "baseline", 0) != 0 for m in report.metric_deltas)
            
            if not has_baseline:
                rows.append(["Metric", "Value"])
                for m in report.metric_deltas:
                    rows.append([m.name.title(), f"${m.current:,.2f}"])
            else:
                rows.append(["Metric", "Current", "Baseline", "Change"])
                for m in report.metric_deltas:
                    sign = "+" if m.percent_change >= 0 else ""
                    rows.append([
                        m.name.title(),
                        f"${m.current:,.2f}",
                        f"${m.baseline:,.2f}",
                        f"{sign}{m.percent_change:.1f}%",
                    ])
            
            t = Table(rows, hAlign="LEFT")
            t.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 4),
                ("FONTSIZE", (0, 1), (-1, -1), 11),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, HexColor("#e5e7eb")),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#f3f4f6")),
            ]))
            story.append(t)
        except Exception:
            for m in report.metric_deltas:
                story.append(Paragraph(f"{m.name.title()}: ${m.current:,.2f}", BodyStyle))
    else:
        story.append(Paragraph("<i>No metrics available.</i>", BodyStyle))
    
    story.append(Spacer(1, 0.24 * inch))
    story.append(HRFlowable(width="100%", color=HexColor("#e5e7eb")))
    story.append(Spacer(1, 0.18 * inch))

    # ------------------------------------------------------------------
    # Section 6 — Insights
    # ------------------------------------------------------------------
    story.append(Paragraph("Insights", HeadingStyle))

    if report.insights:
        for ins in report.insights:
            severity_colors = {
                "high": "#dc2626",      # Red
                "medium": "#f59e0b",    # Orange  
                "low": "#3b82f6",       # Blue
            }
            severity_color = severity_colors.get(ins.severity.lower(), "#6b7280")

            insight_header = (
                f"<font name='Helvetica-Bold' size='13' color='{severity_color}'>"
                f"[{ins.severity.upper()}]</font> "
                f"<font name='Helvetica-Bold' size='13'>{ins.title}</font>"
            )
            story.append(Paragraph(insight_header, BodyStyle))
            story.append(Spacer(1, 0.06 * inch))
            
            story.append(Paragraph(f"<b>Observation:</b> {ins.description}", BodyStyle))
            
            if hasattr(ins, 'driver') and ins.driver:
                story.append(Paragraph(f"<b>Driver:</b> {ins.driver}", BodyStyle))
            if hasattr(ins, 'implication') and ins.implication:
                story.append(Paragraph(f"<b>Implication:</b> {ins.implication}", BodyStyle))
            if hasattr(ins, 'action_direction') and ins.action_direction:
                story.append(Paragraph(f"<b>Action Direction:</b> {ins.action_direction}", BodyStyle))
            if hasattr(ins, 'confidence') and ins.confidence:
                conf_text = f"<b>Confidence:</b> {ins.confidence}"
                if hasattr(ins, 'confidence_basis') and ins.confidence_basis:
                    conf_text += f" ({ins.confidence_basis})"
                story.append(Paragraph(conf_text, BodyStyle))
            
            story.append(Spacer(1, 0.18 * inch))
    else:
        story.append(Paragraph("<i>No significant insights detected in the analysis.</i>", BodyStyle))

    # ------------------------------------------------------------------
    # Section 7 — Business Interpretation (if business_insights present)
    # ------------------------------------------------------------------
    if business_insights:
        try:
            story.append(Spacer(1, 0.24 * inch))
            story.append(HRFlowable(width="100%", color=HexColor("#e5e7eb")))
            story.append(Spacer(1, 0.18 * inch))
            story.append(Paragraph("Business Interpretation", HeadingStyle))
            story.append(Spacer(1, 0.12 * inch))

            def render_enriched_insight(name: str, insight: dict) -> None:
                if not insight:
                    return
                story.append(Paragraph(name, SubheadingStyle))
                if insight.get("description"):
                    story.append(Paragraph(insight["description"], BodyStyle))
                story.append(Spacer(1, 0.12 * inch))

            render_enriched_insight("Trend Analysis", business_insights.get("trend"))
            render_enriched_insight("Revenue Stability", business_insights.get("stability"))
            render_enriched_insight("Revenue Efficiency", business_insights.get("efficiency"))
            render_enriched_insight("Revenue Concentration", business_insights.get("concentration"))

            # ------------------------------------------------------------------
            # Section 8 — Executive Summary (Final)
            # ------------------------------------------------------------------
            exec_summary = business_insights.get("executive_summary")
            if exec_summary:
                story.append(Spacer(1, 0.24 * inch))
                story.append(Paragraph("Executive Summary", section_heading_style))
                story.append(Paragraph(exec_summary, SummaryStyle))
        except Exception:
            pass

    # Build PDF (IO + layout only; no contract changes)
    doc.build(story)
