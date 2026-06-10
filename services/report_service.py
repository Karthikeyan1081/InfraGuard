import os
import json
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute total page counts
    and draw consistent headers, footers, and page numbers.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, page_count: int):
        self.saveState()
        
        # Colors
        primary_color = colors.HexColor("#1E293B")
        gray_text = colors.HexColor("#64748B")
        divider_color = colors.HexColor("#E2E8F0")
        
        # 1. Header (pages after Page 1)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(primary_color)
            self.drawString(54, 755, "AssetSync Reconciliation Audit Report")
            self.setFont("Helvetica", 8)
            self.setFillColor(gray_text)
            self.drawRightString(558, 755, "Confidential Infrastructure Report")
            
            # Divider line
            self.setStrokeColor(divider_color)
            self.setLineWidth(0.75)
            self.line(54, 747, 558, 747)
            
        # 2. Footer (all pages)
        self.setStrokeColor(divider_color)
        self.setLineWidth(0.75)
        self.line(54, 50, 558, 50)
        
        self.setFont("Helvetica", 8)
        self.setFillColor(gray_text)
        self.drawString(54, 38, "AssetSync Inventory Reconciliation Engine (AI-Free Audit)")
        
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 38, page_str)
        
        self.restoreState()


class ReportService:
    @staticmethod
    def _get_severity_color(severity: str) -> colors.Color:
        sev = severity.lower()
        if sev == "high":
            return colors.HexColor("#EF4444")  # Red
        if sev == "medium":
            return colors.HexColor("#F59E0B")  # Amber
        return colors.HexColor("#10B981")  # Emerald Green

    @classmethod
    async def generate_pdf(
        cls,
        analysis_id: str,
        name: str,
        cmdb_file: str,
        actual_file: str,
        created_at: str,
        summary_stats: Dict[str, Any],
        discrepancies: List[Dict[str, Any]],
        findings: List[Dict[str, Any]]
    ) -> str:
        """
        Generates a professional PDF report containing the audit reconciliation results.
        Returns the absolute path to the generated PDF.
        """
        os.makedirs(REPORTS_DIR, exist_ok=True)
        pdf_filename = f"reconciliation_report_{analysis_id}.pdf"
        pdf_path = os.path.join(REPORTS_DIR, pdf_filename)
        
        # Styles Setup
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            name="ReportTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=15
        )
        
        section_style = ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1E293B"),
            spaceBefore=15,
            spaceAfter=8,
            keepWithNext=True
        )
        
        body_style = ParagraphStyle(
            name="BodyNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155")
        )
        
        meta_label_style = ParagraphStyle(
            name="MetaLabel",
            parent=body_style,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1E293B")
        )
        
        table_header_style = ParagraphStyle(
            name="TableHeader",
            parent=body_style,
            fontName="Helvetica-Bold",
            textColor=colors.white
        )
        
        badge_style = ParagraphStyle(
            name="BadgeText",
            parent=body_style,
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=colors.white,
            alignment=1  # Centered
        )

        story = []
        
        # --- TITLE BLOCK ---
        story.append(Paragraph("AssetSync Audit Report", title_style))
        story.append(Paragraph("Infrastructure Inventory Reconciliation & Risk Assessment Summary", body_style))
        story.append(Spacer(1, 15))
        
        # --- METADATA SECTION ---
        # Convert created_at timestamp
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            formatted_date = dt.strftime("%B %d, %Y at %I:%M %p UTC")
        except Exception:
            formatted_date = created_at
            
        meta_data = [
            [Paragraph("Reconciliation Name:", meta_label_style), Paragraph(name, body_style)],
            [Paragraph("Execution Timestamp:", meta_label_style), Paragraph(formatted_date, body_style)],
            [Paragraph("CMDB Source (Expected):", meta_label_style), Paragraph(os.path.basename(cmdb_file), body_style)],
            [Paragraph("Infrastructure Source (Actual):", meta_label_style), Paragraph(os.path.basename(actual_file), body_style)],
        ]
        
        meta_table = Table(meta_data, colWidths=[150, 354])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor("#F1F5F9")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 20))
        
        # --- SUMMARY / STATS SECTION ---
        story.append(Paragraph("Executive Metrics Summary", section_style))
        
        # Stats layout grid
        stats_data = [
            [
                Paragraph("<b>Total Discrepancies</b>", body_style),
                Paragraph(f"<b>{summary_stats.get('total_discrepancies', 0)}</b>", body_style),
                Paragraph("<b>High Severity</b>", body_style),
                Paragraph(f"<font color='red'><b>{summary_stats.get('high_severity', 0)}</b></font>", body_style)
            ],
            [
                Paragraph("Missing Assets", body_style),
                Paragraph(str(summary_stats.get("missing", 0)), body_style),
                Paragraph("Medium Severity", body_style),
                Paragraph(f"<font color='orange'><b>{summary_stats.get('medium_severity', 0)}</b></font>", body_style)
            ],
            [
                Paragraph("Untracked Assets", body_style),
                Paragraph(str(summary_stats.get("untracked", 0)), body_style),
                Paragraph("Low Severity", body_style),
                Paragraph(f"<font color='green'><b>{summary_stats.get('low_severity', 0)}</b></font>", body_style)
            ],
            [
                Paragraph("Naming & Attribute Mismatches", body_style),
                Paragraph(str(summary_stats.get("naming_mismatch", 0) + summary_stats.get("attribute_mismatch", 0)), body_style),
                Paragraph("Duplicate Records", body_style),
                Paragraph(str(summary_stats.get("duplicate", 0)), body_style)
            ]
        ]
        
        stats_table = Table(stats_data, colWidths=[160, 92, 160, 92])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 20))
        
        # --- STRUCTURAL AUDIT FINDINGS (INVESTIGATION PATTERNS) ---
        if findings:
            story.append(Paragraph("Systemic Investigation Findings", section_style))
            for f in findings:
                sev_color = cls._get_severity_color(f["severity"])
                finding_box_data = [
                    [
                        Paragraph(f"<b>{f['title']}</b>", ParagraphStyle("FindTitle", parent=body_style, fontName="Helvetica-Bold", textColor=colors.HexColor("#0F172A"))),
                        Paragraph(f["severity"].upper(), ParagraphStyle("FindSev", parent=badge_style, textColor=sev_color))
                    ],
                    [
                        Paragraph(f["description"], body_style),
                        ""
                    ]
                ]
                finding_box_table = Table(finding_box_data, colWidths=[420, 84])
                finding_box_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
                    ('SPAN', (0, 1), (1, 1)),
                    ('PADDING', (0, 0), (-1, -1), 6),
                    ('LINELEFT', (0, 0), (0, -1), 4, sev_color),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                story.append(finding_box_table)
                story.append(Spacer(1, 8))
            story.append(Spacer(1, 12))

        # --- DISCREPANCIES DETAIL TABLE ---
        story.append(Paragraph("Detailed Discrepancies Inventory", section_style))
        
        if not discrepancies:
            story.append(Paragraph("No discrepancies detected. Infrastructure configuration aligns 100% with CMDB targets.", body_style))
        else:
            # Table Header
            table_data = [[
                Paragraph("Type", table_header_style),
                Paragraph("Severity", table_header_style),
                Paragraph("Asset Identifiers", table_header_style),
                Paragraph("Details & Remediation Guidelines", table_header_style)
            ]]
            
            # Populate Discrepancies rows
            for disc in discrepancies:
                disc_type_str = disc["type"].replace("_", " ").title()
                
                # Format identifiers string
                identifiers = []
                if disc.get("external_id"):
                    identifiers.append(f"<b>ID:</b> {disc['external_id']}")
                if disc.get("hostname_cmdb") or disc.get("hostname_actual"):
                    host_val = disc.get("hostname_actual") or disc.get("hostname_cmdb")
                    identifiers.append(f"<b>Host:</b> {host_val}")
                if disc.get("ip_cmdb") or disc.get("ip_actual"):
                    ip_val = disc.get("ip_actual") or disc.get("ip_cmdb")
                    identifiers.append(f"<b>IP:</b> {ip_val}")
                identifiers_html = "<br/>".join(identifiers) if identifiers else "N/A"
                
                # Detail + Recommendation html
                desc = disc["description"]
                remediation = disc["remediation"]
                detail_text = f"<b>Observation:</b> {desc}<br/><Spacer height=4/><b>Remediation:</b> {remediation}"
                
                # Severity Color Cell styling
                sev_color = cls._get_severity_color(disc["severity"])
                sev_text = f"<font color='white'><b>{disc['severity'].upper()}</b></font>"
                sev_paragraph = Paragraph(sev_text, badge_style)
                
                # Make cells Paragraphs to support wraps
                type_p = Paragraph(disc_type_str, body_style)
                id_p = Paragraph(identifiers_html, body_style)
                detail_p = Paragraph(detail_text, body_style)
                
                table_data.append([type_p, sev_paragraph, id_p, detail_p])
                
            # Column widths sum up to 504 points (max width within margins)
            disc_table = Table(table_data, colWidths=[76, 50, 114, 264])
            
            # Compile Table Style rules
            t_styles = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")), # Header navy bg
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ]
            
            # Apply dynamic backgrounds for severity badges
            for i in range(1, len(table_data)):
                sev_val = discrepancies[i - 1]["severity"]
                bg_c = cls._get_severity_color(sev_val)
                # Apply background only to the severity column (index 1) for this specific row
                t_styles.append(('BACKGROUND', (1, i), (1, i), bg_c))
                t_styles.append(('ALIGN', (1, i), (1, i), 'CENTER'))
                t_styles.append(('VALIGN', (1, i), (1, i), 'MIDDLE'))
                
            disc_table.setStyle(TableStyle(t_styles))
            story.append(disc_table)
            
        # Build Document
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54
        )
        
        # Build document flow with NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
        return pdf_path
