from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, PageBreak, Preformatted

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / 'submission_report.md'
OUTPUT = ROOT / 'Report.pdf'

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleStyle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=22, leading=28, alignment=TA_CENTER, textColor=colors.HexColor('#0F3D5A')))
styles.add(ParagraphStyle(name='SubtitleStyle', parent=styles['Heading2'], fontName='Helvetica', fontSize=13, leading=18, alignment=TA_CENTER, textColor=colors.HexColor('#4F5B66')))
styles.add(ParagraphStyle(name='SectionStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, leading=18, spaceBefore=16, spaceAfter=8, textColor=colors.HexColor('#0F3D5A')))
styles.add(ParagraphStyle(name='BodyStyle', parent=styles['BodyText'], fontName='Helvetica', fontSize=10.5, leading=14, spaceAfter=6, textColor=colors.HexColor('#22313F')))
styles.add(ParagraphStyle(name='BulletStyle', parent=styles['BodyText'], fontName='Helvetica', fontSize=10.5, leading=14, leftIndent=14, spaceAfter=4, textColor=colors.HexColor('#22313F')))
styles.add(ParagraphStyle(name='CodeStyle', parent=styles['Code'], fontName='Courier', fontSize=8.7, leading=11, leftIndent=8, backColor=colors.HexColor('#F5F7FA'), borderPadding=6, borderWidth=0, spaceAfter=8))


def clean_text(text: str) -> str:
    text = text.strip()
    return text.replace('\\', '/')


def parse_markdown(path: Path):
    lines = path.read_text(encoding='utf-8').splitlines()
    story = []
    in_code = False
    code_lines = []

    def flush_code():
        nonlocal code_lines, in_code
        if code_lines:
            story.append(Preformatted('\n'.join(code_lines), styles['CodeStyle']))
            story.append(Spacer(1, 6))
        code_lines = []
        in_code = False

    for raw_line in lines:
        line = raw_line.rstrip()
        if line.startswith('```'):
            if in_code:
                flush_code()
            else:
                in_code = True
                code_lines = []
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not line.strip():
            continue

        if line.startswith('## '):
            story.append(Paragraph(clean_text(line[3:]), styles['SectionStyle']))
        elif line.startswith('# '):
            story.append(Paragraph(clean_text(line[2:]), styles['SectionStyle']))
        elif line.startswith('- '):
            story.append(Paragraph('• ' + clean_text(line[2:]), styles['BulletStyle']))
        else:
            story.append(Paragraph(clean_text(line), styles['BodyStyle']))

    if in_code:
        flush_code()

    return story


def build_story():
    story = []
    story.append(Paragraph('Distributed Background Job Processing System', styles['TitleStyle']))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph('Professional Assignment Submission Report', styles['SubtitleStyle']))
    story.append(Spacer(1, 0.6 * inch))
    story.append(Paragraph('This document presents the completed system architecture, implementation highlights, dashboard design, testing evidence, and run instructions for the assignment.', styles['BodyStyle']))
    story.append(Paragraph('Prepared for submission with a polished academic-style format.', styles['BodyStyle']))
    story.append(PageBreak())
    story.extend(parse_markdown(INPUT))
    return story


def main():
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=0.75 * inch, rightMargin=0.75 * inch, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    story = build_story()
    doc.build(story)
    print(f'Created {OUTPUT}')


if __name__ == '__main__':
    main()
