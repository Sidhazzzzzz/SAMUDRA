from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from datetime import datetime

def generate_pdf_advisory(state_dict: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=40, leftMargin=40,
                            topMargin=40, bottomMargin=40)
    
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1 # Center
    
    h2_style = styles['Heading2']
    normal_style = styles['Normal']
    
    elements = []
    
    # Header
    elements.append(Paragraph("ORCA - Maritime Advisory Bulletin", title_style))
    elements.append(Spacer(1, 12))
    
    time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    elements.append(Paragraph(f"Generated at: {time_str}", normal_style))
    elements.append(Paragraph(f"Original Query: {state_dict.get('user_query', '')}", normal_style))
    elements.append(Spacer(1, 20))
    
    # Verdict
    verdict = state_dict.get('verdict', {})
    if verdict:
        status = verdict.get('verdict', 'UNKNOWN')
        reason = verdict.get('reason', '')
        
        status_color = colors.green if status == "SAFE" else colors.red if status == "NO-GO" else colors.orange
        
        v_style = ParagraphStyle(
            'Verdict',
            parent=styles['Heading2'],
            textColor=status_color
        )
        elements.append(Paragraph(f"SYSTEM STATUS: {status}", v_style))
        elements.append(Paragraph(f"Reason: {reason}", normal_style))
        elements.append(Spacer(1, 20))
        
    # Weather
    weather = state_dict.get('weather_risks', [])
    if weather and len(weather) > 0:
        w = weather[0]
        elements.append(Paragraph("Weather Conditions", h2_style))
        elements.append(Paragraph(f"Summary: {w.get('summary', 'N/A')}", normal_style))
        elements.append(Paragraph(f"Wave Height: {w.get('wave_height_m', 'N/A')} m", normal_style))
        elements.append(Paragraph(f"Wind Speed: {w.get('wind_speed_knots', 'N/A')} knots", normal_style))
        elements.append(Spacer(1, 20))
        
    # Data Provenance (Trace)
    elements.append(Paragraph("Data Provenance & Trace", h2_style))
    trace = state_dict.get('execution_trace', [])
    
    if trace:
        data = [["Stage", "Source Type", "Duration (ms)", "Summary"]]
        for t in trace:
            data.append([
                t.get('stage', ''),
                t.get('source_type', ''),
                str(t.get('duration_ms', '')),
                t.get('summary', '')[:50] + ('...' if len(t.get('summary', '')) > 50 else '')
            ])
            
        t_style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E2B3C')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F5F5F5')),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('FONTSIZE', (0,1), (-1,-1), 8),
        ])
        table = Table(data, colWidths=[120, 70, 70, 250])
        table.setStyle(t_style)
        elements.append(table)
    else:
        elements.append(Paragraph("No trace available.", normal_style))
        
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

# Alias for compatibility with orchestrator.py
generate_advisory = generate_pdf_advisory
