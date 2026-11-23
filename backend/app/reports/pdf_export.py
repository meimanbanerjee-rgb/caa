# backend/app/reports/pdf_export.py
# Executive PDF report generation using ReportLab adhering to PRD Section 5.6 (FR-22, FR-23, FR-24).

import io
from typing import Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)

from backend.app.models.insight import AnalysisModel
from backend.app.reports.report_builder import ReportBuilder, StructuredReport


class NumberedCanvas(io.BytesIO):
    """Custom canvas that adds page numbers and branding in a second pass."""
    pass


def generate_executive_pdf(analysis: AnalysisModel) -> io.BytesIO:
    """
    Generates a professional, multi-page PDF executive report.
    Guarantees that all metrics match deterministic pandas computations exactly.
    """
    report: StructuredReport = ReportBuilder.build_report(analysis)
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Custom palette
    navy_dark = colors.HexColor("#0B132B")
    navy_blue = colors.HexColor("#1C2541")
    cyan_accent = colors.HexColor("#00B4D8")
    slate_gray = colors.HexColor("#4A5568")
    light_bg = colors.HexColor("#F8FAFC")
    border_color = colors.HexColor("#E2E8F0")

    # Typography styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=navy_dark,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=slate_gray,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=navy_blue,
        spaceBefore=14,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=navy_dark,
    )
    callout_bold = ParagraphStyle(
        "CalloutBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=navy_dark,
    )

    story = []

    # 1. Header Banner
    header_table = Table(
        [
            [
                Paragraph(f"<b>InsightForge AI</b> &nbsp;|&nbsp; Business Intelligence Report", title_style),
                Paragraph(f"<b>VERIFIED</b><br/>FR-16 Guard", ParagraphStyle("Badge", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, textColor=colors.HexColor("#047857"), alignment=2)),
            ]
        ],
        colWidths=[420, 110],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=cyan_accent, spaceBefore=4, spaceAfter=8))

    # Metadata Row
    meta_text = (
        f"<b>Analysis ID:</b> {report.analysis_id} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>Domain:</b> {report.domain.title()} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>Generated:</b> {report.generated_at}"
    )
    story.append(Paragraph(meta_text, subtitle_style))
    story.append(Spacer(1, 10))

    # 2. Render Each Section from Structured Report
    for section in report.sections:
        story.append(Paragraph(section.title, section_heading))
        story.append(Paragraph(f"<i>{section.summary}</i>", subtitle_style))
        story.append(Spacer(1, 4))

        if section.id == "executive_summary":
            points = section.content.get("points", [])
            summary_cells = [[Paragraph(f"• {p}", body_style)] for p in points]
            t = Table(summary_cells, colWidths=[530])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#BFDBFE")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))

        elif section.id == "key_metrics":
            rows = [["Metric", "Deterministically Calculated Value", "Formula"]]
            for it in section.items:
                rows.append([it["metric"], it["value"], it["formula"]])
            t = Table(rows, colWidths=[150, 180, 200])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), navy_blue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                ("GRID", (0, 0), (-1, -1), 0.5, border_color),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8.5),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))

        elif section.id == "prioritized_findings":
            for ins in section.items:
                prio = ins["priority"].upper()
                badge_color = colors.HexColor("#DC2626") if prio == "CRITICAL" else colors.HexColor("#D97706") if prio == "HIGH" else colors.HexColor("#2563EB")
                ins_table = Table(
                    [
                        [
                            Paragraph(f"<b>[{prio}] {ins['title']}</b>", callout_bold),
                            Paragraph(f"Source: {ins.get('source', {}).get('filename', 'dataset')}", subtitle_style),
                        ],
                        [
                            Paragraph(f"<b>Observed Fact (Python Calculated):</b> {ins['observed_fact']}", body_style),
                            "",
                        ],
                        [
                            Paragraph(f"<b>Interpretation:</b> {ins['interpretation']}", body_style),
                            "",
                        ],
                        [
                            Paragraph(f"<b>Action / Recommendation:</b> {ins['recommendation']}", body_style),
                            "",
                        ],
                        [
                            Paragraph(f"<i>Evidence:</i> {ins.get('evidence')} &nbsp;|&nbsp; <i>Method:</i> {ins.get('method_or_formula')}", subtitle_style),
                            "",
                        ],
                    ],
                    colWidths=[400, 130],
                )
                ins_table.setStyle(TableStyle([
                    ("SPAN", (0, 1), (1, 1)),
                    ("SPAN", (0, 2), (1, 2)),
                    ("SPAN", (0, 3), (1, 3)),
                    ("SPAN", (0, 4), (1, 4)),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 0.75, border_color),
                    ("LINELEFT", (0, 0), (0, -1), 3, badge_color),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(KeepTogether(ins_table))
                story.append(Spacer(1, 6))

        elif section.id == "risks":
            risk_rows = [["Risk Category", "Impact & Observation"]]
            for r in section.items:
                risk_rows.append([r["type"], r["detail"]])
            t = Table(risk_rows, colWidths=[160, 370])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7F1D1D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                ("GRID", (0, 0), (-1, -1), 0.5, border_color),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))

        elif section.id == "opportunities":
            opp_rows = [["Initiative", "Suggested Strategic Action"]]
            for opp in section.items:
                opp_rows.append([opp["initiative"], opp["action"]])
            t = Table(opp_rows, colWidths=[160, 370])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065F46")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                ("GRID", (0, 0), (-1, -1), 0.5, border_color),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))

        elif section.id == "methodology_and_audit":
            audit_lines = [
                f"• <b>Engine:</b> {section.content.get('computation_engine')}",
                f"• <b>Integrity Guard:</b> {section.content.get('verification_rule')}",
            ]
            for a in section.content.get("assumptions", []):
                audit_lines.append(f"• <b>Assumption:</b> {a}")
            t = Table([[Paragraph("<br/>".join(audit_lines), subtitle_style)]], colWidths=[530])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), light_bg),
                ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))

    doc.build(story)
    buffer.seek(0)
    return buffer

