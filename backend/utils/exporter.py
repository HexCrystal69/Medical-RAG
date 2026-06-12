"""
Exporter Utility Module
------------------------
Generates formatted reports in TXT or PDF formats.
Enables export of chat logs, research summaries, and quality benchmarks.
"""

from io import BytesIO
from typing import List, Dict, Any

class Exporter:
    """Generates file streams for exporting medical analysis data."""

    @staticmethod
    def to_txt(title: str, sections: List[Dict[str, str]]) -> bytes:
        """Export content as a formatted plain text byte string."""
        lines = []
        lines.append("=" * 60)
        lines.append(f"  {title.upper()}")
        lines.append("=" * 60)
        lines.append("")

        for section in sections:
            lines.append(f"--- {section['header'].upper()} ---")
            lines.append(section['body'])
            lines.append("")
        
        return "\n".join(lines).encode("utf-8")

    @staticmethod
    def to_pdf(title: str, sections: List[Dict[str, str]]) -> bytes:
        """Export content as a styled PDF using ReportLab (safely wrapped)."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors

            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
            )
            story = []

            styles = getSampleStyleSheet()

            # Custom premium styles
            title_style = ParagraphStyle(
                'ReportTitle',
                parent=styles['Heading1'],
                fontSize=22,
                leading=26,
                textColor=colors.HexColor('#0F172A'),  # Slate-900
                spaceAfter=20
            )
            header_style = ParagraphStyle(
                'SectionHeader',
                parent=styles['Heading2'],
                fontSize=14,
                leading=18,
                textColor=colors.HexColor('#1E3A8A'),  # Navy-900
                spaceBefore=15,
                spaceAfter=8
            )
            body_style = ParagraphStyle(
                'ReportBody',
                parent=styles['Normal'],
                fontSize=10,
                leading=14,
                textColor=colors.HexColor('#334155'),  # Slate-700
                spaceAfter=10
            )

            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 10))

            for section in sections:
                story.append(Paragraph(section['header'], header_style))
                story.append(Spacer(1, 4))
                # Replace newlines with HTML breaks for PDF formatting
                body_html = section['body'].replace('\n', '<br/>')
                story.append(Paragraph(body_html, body_style))
                story.append(Spacer(1, 8))

            doc.build(story)
            pdf_bytes = buffer.getvalue()
            buffer.close()
            return pdf_bytes

        except ImportError:
            # Fallback if ReportLab is not available
            print("[WARNING] reportlab is not installed. Falling back to plain text PDF container.")
            fallback_text = f"PDF EXPORT ERROR: reportlab library not found.\n\nRaw Report Content:\n\n"
            fallback_bytes = Exporter.to_txt(title, sections)
            return fallback_text.encode("utf-8") + fallback_bytes
