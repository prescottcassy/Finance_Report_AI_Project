from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
import os
import re
from datetime import datetime


def _ordinal_day(day):
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def _format_cover_date(date_text):
    if date_text:
        return date_text
    now = datetime.now()
    return f"{now.strftime('%B')} {_ordinal_day(now.day)}, {now.year}"


def _draw_cover_background(canvas, _doc):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#232529"))
    canvas.rect(0, 0, letter[0], letter[1], stroke=0, fill=1)
    canvas.restoreState()

def _display_value(value, fallback="Not provided"):
    value = (value or "").strip()
    return value if value else fallback


def _escape_paragraph_text(text):
    """Escape text for ReportLab Paragraph and normalize awkward line wraps.

    Single newlines are treated as soft wraps and converted to spaces.
    Blank-line paragraph breaks are preserved.
    """
    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not raw:
        return ""

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    normalized = []
    for paragraph in paragraphs:
        lines = [line.strip() for line in paragraph.split("\n") if line.strip()]
        # Preserve list-like content on separate lines.
        if any(line.startswith(("-", "*", "•")) for line in lines):
            normalized.append("<br/>".join(lines))
        else:
            normalized.append(" ".join(lines))

    safe = "<br/><br/>".join(normalized)
    safe = safe.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return safe.replace("&lt;br/&gt;", "<br/>")


def _has_text(value):
    """Return True when a value contains visible text."""
    return bool((value or "").strip())


def _get_friendly_section_title(section_title):
    """Map section titles to more descriptive book chapter-style names."""
    title_lower = section_title.lower()
    title_map = {
        'risk factors': 'Understanding the Threats and Challenges Ahead',
        'management discussion and analysis': 'How the Business Performed and What Drives Results',
        'md&a': 'How the Business Performed and What Drives Results',
        'financials': 'The Numbers Behind the Story',
        'financial health': 'The Numbers Behind the Story',
    }
    return title_map.get(title_lower, section_title)


def create_pdf_report(
    company_name,
    fiscal_year,
    bluf,
    narrative,
    sections,
    output_path,
    course_name=None,
    professor_name=None,
    generated_on=None,
    bluf_prompt=None,
    narrative_prompt=None,
    financial_metrics=None,
    report_type="analysis",
):
    """
    Create a PDF report with the 10-K analysis and prompts used
    """
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                          rightMargin=0.4*inch, leftMargin=0.4*inch,
                          topMargin=0.6*inch, bottomMargin=0.6*inch)
    
    story = []
    styles = getSampleStyleSheet()
    cover_date = _format_cover_date(generated_on)
    cover_course = _display_value(
        course_name or os.getenv("COURSE_NAME"),
        "ITAI 3378 Finance and Business AI\nSpring 2026",
    )
    cover_professor = _display_value(
        professor_name or os.getenv("PROFESSOR_NAME"),
        "Karthik Rajan",
    )
    
    # Custom styles
    cover_company_style = ParagraphStyle(
        'CoverCompany',
        parent=styles['Heading1'],
        fontSize=23,
        textColor=colors.HexColor('#aac8f6'),
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    cover_report_style = ParagraphStyle(
        'CoverReport',
        parent=styles['Normal'],
        fontSize=16,
        textColor=colors.HexColor('#82afe8'),
        alignment=TA_CENTER,
        leading=20,
        spaceAfter=2,
        fontName='Helvetica'
    )

    cover_fiscal_style = ParagraphStyle(
        'CoverFiscal',
        parent=styles['Normal'],
        fontSize=10.5,
        textColor=colors.HexColor('#bfc7d4'),
        alignment=TA_CENTER,
        leading=15,
        spaceAfter=12,
        fontName='Helvetica-Oblique'
    )

    cover_meta_style = ParagraphStyle(
        'CoverMeta',
        parent=styles['Normal'],
        fontSize=10.5,
        textColor=colors.HexColor('#89b9f0'),
        alignment=TA_CENTER,
        leading=14,
        fontName='Helvetica'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#374151'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        alignment=TA_JUSTIFY,
        spaceAfter=10,
        leading=14
    )
    
    metric_value_style = ParagraphStyle(
        'MetricValue',
        parent=styles['Normal'],
        fontSize=15.5,
        textColor=colors.HexColor('#8ec0ff'),
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        leading=17,
    )

    metric_label_style = ParagraphStyle(
        'MetricLabel',
        parent=styles['Normal'],
        fontSize=8.8,
        textColor=colors.HexColor('#edf2ff'),
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        leading=10,
    )

    metric_subtext_style = ParagraphStyle(
        'MetricSubtext',
        parent=styles['Normal'],
        fontSize=7.8,
        textColor=colors.HexColor('#c6d0e5'),
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique',
        leading=9,
    )
    
    # Page 1: Dark cover with title, metrics, and class attribution
    story.append(Spacer(1, 0.8*inch))
    story.append(Paragraph(_escape_paragraph_text(str(company_name).upper()), cover_company_style))
    report_title = "Analysis Verification Report" if report_type == "verification" else "Financial Storytelling Report"
    story.append(Paragraph(report_title, cover_report_style))
    story.append(Paragraph(f"Fiscal Year {fiscal_year}", cover_fiscal_style))
    story.append(Spacer(1, 0.12*inch))

    metrics = financial_metrics or []
    if metrics:
        row = []
        for metric in metrics[:4]:
            value = _escape_paragraph_text(_display_value(metric.get("title"), "N/A"))
            label = _escape_paragraph_text(_display_value(metric.get("label"), ""))
            subtext = _escape_paragraph_text(metric.get("subtext", ""))
            metric_cell = [
                Paragraph(value, metric_value_style),
                Spacer(1, 0.03*inch),
                Paragraph(label, metric_label_style),
                Spacer(1, 0.02*inch),
                Paragraph(subtext or "&nbsp;", metric_subtext_style),
            ]
            row.append(metric_cell)

        while len(row) < 4:
            row.append([
                Paragraph("N/A", metric_value_style),
                Spacer(1, 0.03*inch),
                Paragraph("", metric_label_style),
                Spacer(1, 0.02*inch),
                Paragraph("&nbsp;", metric_subtext_style),
            ])

        metrics_table = Table([row], colWidths=[1.58*inch, 1.58*inch, 1.58*inch, 1.58*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#34363b')),
            ('INNERGRID', (0, 0), (-1, -1), 0.6, colors.HexColor('#646a75')),
            ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#646a75')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 11),
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 0.48*inch))

    cover_course_single_line = " ".join(str(cover_course).splitlines()).strip()
    cover_meta_lines = [
        f"Date: {cover_date}",
        f"Course: {cover_course_single_line}",
        f"Professor: {cover_professor}",
    ]
    story.append(Spacer(1, 0.04*inch))
    for line in cover_meta_lines:
        story.append(Paragraph(_escape_paragraph_text(line), cover_meta_style))

    story.append(PageBreak())

    # BLUF + Story: keep continuous flow and avoid forced blank pages.
    if _has_text(bluf):
        story.append(Paragraph("BOTTOM LINE UP FRONT", heading_style))
        story.append(Paragraph(_escape_paragraph_text(bluf), body_style))

    if _has_text(narrative):
        story.append(Spacer(1, 0.06*inch))
        story.append(Paragraph("THE STORY", heading_style))
        story.append(Paragraph(_escape_paragraph_text(narrative), body_style))

    if _has_text(bluf) or _has_text(narrative):
        story.append(Spacer(1, 0.04*inch))
    
    # Pages 3+: Sections with prompts or verification summaries.
    for section in sections:
        # Skip Business Overview section
        title = (section.get('title') or '').strip()
        if not title:
            continue
        if title.lower() == 'business overview':
            continue
        friendly_title = str(_get_friendly_section_title(title) or title)
        story.append(Paragraph(friendly_title.upper(), heading_style))
        story.append(Paragraph(_escape_paragraph_text(_display_value(section.get('summary', ''), '')), body_style))
        story.append(Spacer(1, 0.08*inch))
    
    # Build PDF
    doc.build(story, onFirstPage=_draw_cover_background)
    return output_path
