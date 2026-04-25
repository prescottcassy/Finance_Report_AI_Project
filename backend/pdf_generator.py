from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
import os

def create_pdf_report(company_name, fiscal_year, bluf, narrative, sections, output_path):
    """
    Create a PDF report with the 10-K analysis and prompts used
    """
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                          rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
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
    
    prompt_style = ParagraphStyle(
        'PromptStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#6b7280'),
        spaceAfter=8,
        leftIndent=20,
        leading=11,
        fontName='Courier'
    )
    
    # Page 1: Title and BLUF
    story.append(Paragraph(f"{company_name}", title_style))
    story.append(Paragraph(f"10-K Analysis | Fiscal Year {fiscal_year}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("BOTTOM LINE UP FRONT", heading_style))
    story.append(Paragraph(bluf, body_style))
    story.append(Spacer(1, 0.15*inch))
    
    story.append(Paragraph("Prompt Used:", ParagraphStyle(
        'SubHeading',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#9ca3af'),
        fontName='Helvetica-Oblique'
    )))
    story.append(Paragraph(
        "Based on the company&#39;s 10-K filing analysis, provide a SINGLE powerful sentence for an investor considering whether to buy this stock. Be decisive and direct.",
        prompt_style
    ))
    
    story.append(PageBreak())
    
    # Page 2: Narrative
    story.append(Paragraph("THE STORY", heading_style))
    story.append(Paragraph(narrative, body_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("Prompt Used:", ParagraphStyle(
        'SubHeading',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#9ca3af'),
        fontName='Helvetica-Oblique'
    )))
    story.append(Paragraph(
        "Write a compelling investor narrative that tells the story of this company based on its 10-K filing. Connect the business overview, risks, operations, and financial performance into a cohesive narrative that helps an investor understand the company&#39;s trajectory and competitive position.",
        prompt_style
    ))
    
    story.append(PageBreak())
    
    # Pages 3+: Sections with prompts
    for section in sections:
        story.append(Paragraph(section['title'].upper(), heading_style))
        story.append(Paragraph(section['summary'], body_style))
        story.append(Spacer(1, 0.1*inch))
        
        story.append(Paragraph("Prompt Used:", ParagraphStyle(
            'SubHeading',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#9ca3af'),
            fontName='Helvetica-Oblique'
        )))
        
        prompt_text = f"Analyze this {section['title']} section from a 10-K filing and provide a brief TLDR with the bottom line up front for investors."
        story.append(Paragraph(prompt_text, prompt_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Build PDF
    doc.build(story)
    return output_path
