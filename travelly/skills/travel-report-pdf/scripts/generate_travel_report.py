#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class SkillModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class FlightTicket(SkillModel):
    segment_title: str | None = None
    airline: str | None = None
    flight_number: str | None = None
    origin: str | None = None
    destination: str | None = None
    departure: str | None = None
    arrival: str | None = None
    booking_reference: str | None = None
    ticket_number: str | None = None
    seat: str | None = None
    baggage: str | None = None
    price: str | None = None
    booking_url: str | None = None
    notes: str | None = None


class HotelStay(SkillModel):
    name: str | None = None
    address: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    confirmation_number: str | None = None
    room_type: str | None = None
    price: str | None = None
    booking_url: str | None = None
    phone: str | None = None
    amenities: list[str] = Field(default_factory=list)
    notes: str | None = None


class Activity(SkillModel):
    title: str
    date: str | None = None
    time: str | None = None
    location: str | None = None
    price: str | None = None
    category: str | None = None
    booking_url: str | None = None
    notes: str | None = None


class UsefulLink(SkillModel):
    label: str
    url: str
    description: str | None = None


class Contact(SkillModel):
    name: str
    role: str | None = None
    phone: str | None = None
    email: str | None = None
    url: str | None = None
    notes: str | None = None


class TripReport(SkillModel):
    title: str = "Travel Report"
    traveler_name: str | None = None
    destination: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    summary: str | None = None
    currency: str | None = None
    emergency_info: str | None = None
    tickets: list[FlightTicket] = Field(default_factory=list)
    hotel: HotelStay | None = None
    activities: list[Activity] = Field(default_factory=list)
    useful_links: list[UsefulLink] = Field(default_factory=list)
    contacts: list[Contact] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a travel report PDF from JSON input.")
    parser.add_argument("--input", required=True, help="Path to the input JSON file.")
    parser.add_argument("--output", required=True, help="Path to the output PDF file.")
    parser.add_argument(
        "--font-path",
        help="Optional path to a TTF font file. Useful when you need explicit Unicode support.",
    )
    return parser.parse_args()


def load_report(path: Path) -> TripReport:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return TripReport.model_validate(payload)


def select_font(preferred_font_path: str | None = None) -> str:
    try:
        import reportlab

        reportlab_vera = (
            Path(reportlab.__file__).resolve().parent / "fonts" / "Vera.ttf"
        )
    except Exception:  # noqa: BLE001
        reportlab_vera = None

    candidates = [
        preferred_font_path,
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        str(reportlab_vera) if reportlab_vera else None,
    ]

    for candidate in candidates:
        if not candidate:
            continue
        font_path = Path(candidate)
        if not font_path.exists():
            continue
        font_name = "TravelReportSans"
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
        return font_name

    return "Helvetica"


def build_styles(font_name: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TravelReportTitle",
            parent=base["Title"],
            fontName=font_name,
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#16324F"),
            alignment=TA_LEFT,
            spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "TravelReportSubtitle",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#506070"),
            spaceAfter=10,
        ),
        "heading": ParagraphStyle(
            "TravelReportHeading",
            parent=base["Heading2"],
            fontName=font_name,
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#1F4B6E"),
            spaceBefore=12,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "TravelReportBody",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#1E2933"),
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "TravelReportSmall",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#607080"),
            spaceAfter=4,
        ),
        "label": ParagraphStyle(
            "TravelReportLabel",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#16324F"),
        ),
    }


def text_or_dash(value: str | None) -> str:
    return value.strip() if value and value.strip() else "-"


def paragraph_text(value: str | None) -> str:
    return escape(text_or_dash(value)).replace("\n", "<br/>")


def link_markup(label: str, url: str) -> str:
    return f'<link href="{escape(url)}" color="#155E75">{escape(label)}</link>'


def key_value_table(rows: Iterable[tuple[str, str]], styles: dict[str, ParagraphStyle]) -> Table:
    rendered_rows = []
    for label, value in rows:
        rendered_rows.append(
            [
                Paragraph(escape(label), styles["label"]),
                Paragraph(value, styles["body"]),
            ]
        )

    table = Table(rendered_rows, colWidths=[45 * mm, 125 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#D5DEE7")),
            ]
        )
    )
    return table


def section_rule() -> HRFlowable:
    return HRFlowable(
        width="100%",
        thickness=0.8,
        color=colors.HexColor("#D5DEE7"),
        spaceBefore=2,
        spaceAfter=8,
    )


def section_heading(title: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(escape(title), styles["heading"])


def build_story(report: TripReport, styles: dict[str, ParagraphStyle]) -> list:
    story: list = []
    story.append(Paragraph(escape(report.title), styles["title"]))

    subtitle_bits = []
    if report.destination:
        subtitle_bits.append(report.destination)
    if report.start_date or report.end_date:
        subtitle_bits.append(f"{text_or_dash(report.start_date)} to {text_or_dash(report.end_date)}")
    subtitle_bits.append(f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    story.append(Paragraph(escape(" | ".join(subtitle_bits)), styles["subtitle"]))

    story.append(
        key_value_table(
            [
                ("Traveler", paragraph_text(report.traveler_name)),
                ("Destination", paragraph_text(report.destination)),
                ("Dates", paragraph_text(format_date_range(report.start_date, report.end_date))),
                ("Currency", paragraph_text(report.currency)),
            ],
            styles,
        )
    )

    if report.summary:
        story.append(Spacer(1, 6))
        story.append(Paragraph(paragraph_text(report.summary), styles["body"]))

    if report.emergency_info:
        story.append(Paragraph(f"Emergency: {paragraph_text(report.emergency_info)}", styles["small"]))

    add_flights_section(story, report, styles)
    add_hotel_section(story, report, styles)
    add_activities_section(story, report, styles)
    add_links_section(story, report, styles)
    add_contacts_section(story, report, styles)
    add_checklist_section(story, report, styles)
    add_notes_section(story, report, styles)
    return story


def format_date_range(start_date: str | None, end_date: str | None) -> str:
    if start_date and end_date:
        return f"{start_date} to {end_date}"
    return start_date or end_date or "-"


def add_flights_section(story: list, report: TripReport, styles: dict[str, ParagraphStyle]) -> None:
    story.append(section_heading("Flights", styles))
    story.append(section_rule())
    if not report.tickets:
        story.append(Paragraph("No flight details included.", styles["body"]))
        return

    for index, ticket in enumerate(report.tickets, start=1):
        title = ticket.segment_title or f"Flight {index}"
        story.append(Paragraph(escape(title), styles["body"]))
        story.append(
            key_value_table(
                [
                    ("Airline", paragraph_text(ticket.airline)),
                    ("Flight number", paragraph_text(ticket.flight_number)),
                    ("Route", paragraph_text(format_route(ticket.origin, ticket.destination))),
                    ("Departure", paragraph_text(ticket.departure)),
                    ("Arrival", paragraph_text(ticket.arrival)),
                    ("Booking reference", paragraph_text(ticket.booking_reference)),
                    ("Ticket number", paragraph_text(ticket.ticket_number)),
                    ("Seat", paragraph_text(ticket.seat)),
                    ("Baggage", paragraph_text(ticket.baggage)),
                    ("Price", paragraph_text(ticket.price)),
                    ("Booking link", paragraph_for_link(ticket.booking_url)),
                    ("Notes", paragraph_text(ticket.notes)),
                ],
                styles,
            )
        )
        story.append(Spacer(1, 8))


def add_hotel_section(story: list, report: TripReport, styles: dict[str, ParagraphStyle]) -> None:
    story.append(section_heading("Hotel", styles))
    story.append(section_rule())
    if not report.hotel:
        story.append(Paragraph("No hotel details included.", styles["body"]))
        return

    hotel = report.hotel
    story.append(
        key_value_table(
            [
                ("Name", paragraph_text(hotel.name)),
                ("Address", paragraph_text(hotel.address)),
                ("Check-in", paragraph_text(hotel.check_in)),
                ("Check-out", paragraph_text(hotel.check_out)),
                ("Confirmation", paragraph_text(hotel.confirmation_number)),
                ("Room type", paragraph_text(hotel.room_type)),
                ("Phone", paragraph_text(hotel.phone)),
                ("Price", paragraph_text(hotel.price)),
                ("Booking link", paragraph_for_link(hotel.booking_url)),
                ("Amenities", paragraph_text(", ".join(hotel.amenities) if hotel.amenities else None)),
                ("Notes", paragraph_text(hotel.notes)),
            ],
            styles,
        )
    )


def add_activities_section(story: list, report: TripReport, styles: dict[str, ParagraphStyle]) -> None:
    story.append(section_heading("Activities", styles))
    story.append(section_rule())
    if not report.activities:
        story.append(Paragraph("No activities included.", styles["body"]))
        return

    for activity in report.activities:
        story.append(Paragraph(escape(activity.title), styles["body"]))
        story.append(
            key_value_table(
                [
                    ("Date", paragraph_text(activity.date)),
                    ("Time", paragraph_text(activity.time)),
                    ("Location", paragraph_text(activity.location)),
                    ("Category", paragraph_text(activity.category)),
                    ("Price", paragraph_text(activity.price)),
                    ("Booking link", paragraph_for_link(activity.booking_url)),
                    ("Notes", paragraph_text(activity.notes)),
                ],
                styles,
            )
        )
        story.append(Spacer(1, 8))


def add_links_section(story: list, report: TripReport, styles: dict[str, ParagraphStyle]) -> None:
    story.append(section_heading("Useful Links", styles))
    story.append(section_rule())
    if not report.useful_links:
        story.append(Paragraph("No links included.", styles["body"]))
        return

    for link in report.useful_links:
        story.append(Paragraph(link_markup(link.label, link.url), styles["body"]))
        if link.description:
            story.append(Paragraph(paragraph_text(link.description), styles["small"]))
        story.append(Spacer(1, 4))


def add_contacts_section(story: list, report: TripReport, styles: dict[str, ParagraphStyle]) -> None:
    if not report.contacts:
        return

    story.append(section_heading("Contacts", styles))
    story.append(section_rule())
    for contact in report.contacts:
        story.append(Paragraph(escape(contact.name), styles["body"]))
        story.append(
            key_value_table(
                [
                    ("Role", paragraph_text(contact.role)),
                    ("Phone", paragraph_text(contact.phone)),
                    ("Email", paragraph_text(contact.email)),
                    ("Link", paragraph_for_link(contact.url)),
                    ("Notes", paragraph_text(contact.notes)),
                ],
                styles,
            )
        )
        story.append(Spacer(1, 8))


def add_checklist_section(story: list, report: TripReport, styles: dict[str, ParagraphStyle]) -> None:
    if not report.checklist:
        return

    story.append(section_heading("Checklist", styles))
    story.append(section_rule())
    for item in report.checklist:
        story.append(Paragraph(f"- {escape(item)}", styles["body"]))


def add_notes_section(story: list, report: TripReport, styles: dict[str, ParagraphStyle]) -> None:
    if not report.notes:
        return

    story.append(section_heading("Notes", styles))
    story.append(section_rule())
    for note in report.notes:
        story.append(Paragraph(f"- {escape(note)}", styles["body"]))


def paragraph_for_link(url: str | None) -> str:
    if not url:
        return paragraph_text(None)
    return link_markup(url, url)


def format_route(origin: str | None, destination: str | None) -> str:
    if origin and destination:
        return f"{origin} -> {destination}"
    return origin or destination or "-"


def draw_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#8091A3"))
    canvas.drawRightString(doc.pagesize[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf(report: TripReport, output_path: Path, font_name: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = build_styles(font_name)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=report.title,
        author=report.traveler_name or "Travelly",
    )
    doc.build(build_story(report, styles), onFirstPage=draw_footer, onLaterPages=draw_footer)


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    try:
        report = load_report(input_path)
        font_name = select_font(args.font_path)
        build_pdf(report, output_path, font_name)
    except FileNotFoundError as exc:
        print(f"Input file not found: {exc.filename}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in {input_path}: {exc}", file=sys.stderr)
        return 1
    except ValidationError as exc:
        print("Input JSON failed validation:", file=sys.stderr)
        print(exc, file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to build PDF: {exc}", file=sys.stderr)
        return 1

    print(f"Travel report saved to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
