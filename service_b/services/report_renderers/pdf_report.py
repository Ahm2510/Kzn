from datetime import datetime
from typing import Optional, Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.colors import HexColor
from schemas.insight.report import InsightReport


def render_pdf(report: InsightReport, output_path: str, business_insights: Optional[Dict[str, Any]] = None):
    """
    Render a professional PDF report from an InsightReport.
    Handles page breaks, text wrapping, and empty states gracefully.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Container for the 'Flowable' objects
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = styles['Heading1']
    title_style.alignment = TA_LEFT
    title_style.fontSize = 16
    title_style.spaceAfter = 12
    story.append(Paragraph("Business Insight Report", title_style))
    
    # Generation date
    date_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    date_style = styles['Normal']
    date_style.fontSize = 9
    date_style.textColor = (0.4, 0.4, 0.4)  # Gray color
    story.append(Paragraph(f"Generated on {date_str}", date_style))
    story.append(Spacer(1, 0.3*inch))
    
    # V1.75+ Executive Takeaways section (if business_insights present)
    if business_insights:
        try:
            executive_takeaways = business_insights.get("executive_takeaways")
            if executive_takeaways and isinstance(executive_takeaways, list) and len(executive_takeaways) > 0:
                story.append(Paragraph("Executive Takeaways", heading_style))
                bullet_style = styles['BodyText']
                bullet_style.fontSize = 10
                bullet_style.leading = 14
                for bullet in executive_takeaways[:6]:  # Cap at 6
                    if bullet:
                        story.append(Paragraph(f"• {bullet}", bullet_style))
                        story.append(Spacer(1, 0.05*inch))
                story.append(Spacer(1, 0.2*inch))
            
            # Scope block
            scope = business_insights.get("scope")
            if scope and isinstance(scope, dict):
                analyzed = scope.get("analyzed", [])
                not_analyzed = scope.get("not_analyzed", [])
                if analyzed or not_analyzed:
                    scope_style = ParagraphStyle(
                        'ScopeStyle',
                        parent=styles['Normal'],
                        fontSize=9,
                        textColor=HexColor('#666666'),
                        leading=12,
                    )
                    scope_text = ""
                    if analyzed:
                        scope_text += f"<b>Analyzed:</b> {', '.join(analyzed)}. "
                    if not_analyzed:
                        scope_text += f"<b>Not analyzed:</b> {', '.join(not_analyzed)}."
                    story.append(Paragraph(scope_text, scope_style))
                    story.append(Spacer(1, 0.25*inch))
        except Exception:
            pass  # Defensive - never fail PDF generation for business insights
    
    # Summary section
    heading_style = styles['Heading2']
    heading_style.fontSize = 12
    heading_style.spaceAfter = 6
    story.append(Paragraph("Summary", heading_style))
    
    summary_style = styles['BodyText']
    summary_style.fontSize = 10
    summary_style.leading = 14
    story.append(Paragraph(report.summary, summary_style))
    story.append(Spacer(1, 0.25*inch))
    
    # Key Metrics section
    story.append(Paragraph("Key Metrics", heading_style))
    
    metrics_style = styles['BodyText']
    metrics_style.fontSize = 10
    metrics_style.leading = 14
    
    if report.metric_deltas:
        for m in report.metric_deltas:
            # Format metric display
            if m.baseline == 0:
                # Standalone metric (no baseline)
                metric_text = f"<b>{m.name.title()}:</b> ${m.current:,.2f}"
            else:
                # Comparative metric
                sign = "+" if m.percent_change >= 0 else ""
                metric_text = (
                    f"<b>{m.name.title()}:</b> ${m.current:,.2f} "
                    f"({sign}{m.percent_change:.1f}% vs baseline ${m.baseline:,.2f})"
                )
            story.append(Paragraph(metric_text, metrics_style))
            story.append(Spacer(1, 0.1*inch))
    else:
        story.append(Paragraph("<i>No metrics available.</i>", metrics_style))
    
    story.append(Spacer(1, 0.25*inch))
    
    # Insights section
    story.append(Paragraph("Insights", heading_style))
    
    insights_style = styles['BodyText']
    insights_style.fontSize = 10
    insights_style.leading = 14
    
    if report.insights:
        for ins in report.insights:
            # Format severity with color indication
            severity_color = {
                "high": "#CC0000",    # Red
                "medium": "#FF9900",  # Orange
                "low": "#0066CC"      # Blue
            }.get(ins.severity.lower(), "#666666")
            
            insight_text = (
                f"<b>[<font color='{severity_color}'>{ins.severity.upper()}</font>]</b> "
                f"<b>{ins.title}</b><br/>"
                f"{ins.description}"
            )
            story.append(Paragraph(insight_text, insights_style))
            story.append(Spacer(1, 0.15*inch))
    else:
        story.append(
            Paragraph(
                "<i>No significant insights detected in the analysis.</i>",
                insights_style
            )
        )
    
    # V1.75+ Business Insights detailed sections (if present)
    if business_insights:
        try:
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph("Business Interpretation", heading_style))
            story.append(Spacer(1, 0.1*inch))
            
            detail_style = styles['BodyText']
            detail_style.fontSize = 10
            detail_style.leading = 14
            
            small_style = ParagraphStyle(
                'SmallStyle',
                parent=styles['Normal'],
                fontSize=8,
                textColor=HexColor('#888888'),
                leading=10,
            )
            
            # Helper function to render an enriched insight
            def render_enriched_insight(name: str, insight: dict):
                if not insight:
                    return
                story.append(Paragraph(f"<b>{name}</b>", detail_style))
                
                # Description
                if insight.get("description"):
                    story.append(Paragraph(insight["description"], detail_style))
                
                # Driver
                if insight.get("driver"):
                    story.append(Paragraph(f"<i>Driver:</i> {insight['driver']}", detail_style))
                
                # Implication
                if insight.get("implication"):
                    story.append(Paragraph(f"<i>Implication:</i> {insight['implication']}", detail_style))
                
                # Action Direction
                if insight.get("action_direction"):
                    story.append(Paragraph(f"<i>Action:</i> {insight['action_direction']}", detail_style))
                
                # Confidence with basis
                confidence = insight.get("confidence")
                confidence_basis = insight.get("confidence_basis")
                if confidence:
                    conf_text = f"Confidence: {confidence}"
                    if confidence_basis:
                        conf_text += f" ({confidence_basis})"
                    story.append(Paragraph(conf_text, small_style))
                
                story.append(Spacer(1, 0.15*inch))
            
            # Render each insight type
            render_enriched_insight("Trend Analysis", business_insights.get("trend"))
            render_enriched_insight("Revenue Stability", business_insights.get("stability"))
            render_enriched_insight("Revenue Efficiency", business_insights.get("efficiency"))
            render_enriched_insight("Revenue Concentration", business_insights.get("concentration"))
            
            # Executive Summary at end
            exec_summary = business_insights.get("executive_summary")
            if exec_summary:
                story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph("<b>Executive Summary</b>", detail_style))
                story.append(Paragraph(exec_summary, detail_style))
        except Exception:
            pass  # Defensive - never fail PDF generation
    
    # Build PDF
    doc.build(story)
