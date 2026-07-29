"""Wochenprotokoll als PDF - das digitale Gegenstueck zum Papierbogen,
der in der Wache abgeheftet wird."""

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

WEEKDAYS = [
    "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag",
]
BRAND = colors.HexColor("#17343d")
LINE = colors.HexColor("#aebdb8")
MUTED = colors.HexColor("#53686f")


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "wbTitle", parent=base["Title"], fontSize=16, leading=20,
            alignment=TA_LEFT, textColor=BRAND, spaceAfter=2 * mm,
        ),
        "meta": ParagraphStyle(
            "wbMeta", parent=base["Normal"], fontSize=9, textColor=MUTED,
        ),
        "day": ParagraphStyle(
            "wbDay", parent=base["Heading2"], fontSize=11, leading=14,
            textColor=BRAND, spaceBefore=4 * mm, spaceAfter=1 * mm,
        ),
        "cell": ParagraphStyle(
            "wbCell", parent=base["Normal"], fontSize=9, leading=12,
        ),
        "empty": ParagraphStyle(
            "wbEmpty", parent=base["Normal"], fontSize=9, leading=12, textColor=MUTED,
        ),
    }


def _entry_table(entries, styles):
    if not entries:
        return Paragraph("Keine Eintraege.", styles["empty"])
    rows = [["Prioritaet", "Titel", "Kategorie", "Status", "Erledigt"]]
    for entry in entries:
        rows.append([
            Paragraph(entry.get_priority_display(), styles["cell"]),
            Paragraph(entry.title, styles["cell"]),
            Paragraph(entry.get_category_display(), styles["cell"]),
            Paragraph(entry.get_status_display(), styles["cell"]),
            "[x]" if entry.status == "done" else "[ ]",
        ])
    table = Table(rows, colWidths=[22 * mm, 68 * mm, 30 * mm, 28 * mm, 17 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (4, 1), (4, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def build_week_pdf(buffer, station, year, week, days, general_entries):
    styles = _styles()
    document = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=18 * mm,
        title=f"Wochenprotokoll KW {week}/{year} - {station.name}",
        author=station.name,
    )
    heading = station.name
    if station.location:
        heading = f"{station.name} - {station.location}"

    story = [
        Paragraph("Uebergabeprotokoll", styles["title"]),
        Paragraph(heading, styles["meta"]),
        Paragraph(
            f"Kalenderwoche {week}/{year} &middot; "
            f"{days[0]['date'].strftime('%d.%m.%Y')} bis {days[-1]['date'].strftime('%d.%m.%Y')}",
            styles["meta"],
        ),
        Spacer(1, 4 * mm),
    ]

    for index, day in enumerate(days):
        team = day["team_note"].note if day["team_note"] else "-"
        block = [
            Paragraph(
                f"{WEEKDAYS[index]}, {day['date'].strftime('%d.%m.%Y')} &nbsp;&nbsp; "
                f"<font color='#53686f'>Team: {team}</font>",
                styles["day"],
            ),
            _entry_table(day["entries"], styles),
        ]
        story.append(KeepTogether(block))

    story.append(PageBreak())
    story.append(Paragraph("Allgemeines (ohne Tagesbezug)", styles["day"]))
    story.append(_entry_table(list(general_entries), styles))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "Enthaelt keine Patienten-, Gesundheits- oder Einsatzdaten.", styles["meta"],
    ))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(15 * mm, 10 * mm, f"{station.name} - KW {week}/{year}")
        canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Seite {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer
