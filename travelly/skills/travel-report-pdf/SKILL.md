---
name: travel-report-pdf
description: Generate a travel report PDF when the user wants a trip brief, itinerary handoff, or summary document with tickets, hotel details, activities, useful links, contacts, checklist items, and notes.
---

# Travel Report PDF

Use this skill when the user asks for a PDF trip report, travel brief, itinerary handoff, or a shareable travel summary.

## Workflow

1. Gather the trip information into one JSON payload.
2. Use the shape in `references/example_trip.json`.
3. Run `scripts/run_generate_travel_report.sh`.
4. Always pass an absolute `output` path so the generated PDF survives after the script finishes.

## Script usage

Use:

- `file_path="scripts/run_generate_travel_report.sh"`
- `args.payload-json="<compact JSON string>"`
- `args.output="/absolute/path/to/travel-report.pdf"`

Optional:

- `args.font-path="/absolute/path/to/font.ttf"`
- `args.input-json="/absolute/path/to/trip.json"` for manual testing when a JSON file already exists

## Input guidance

The payload can include:

- `title`, `traveler_name`, `destination`, `start_date`, `end_date`, `summary`, `currency`, `emergency_info`
- `tickets[]`
- `hotel`
- `activities[]`
- `useful_links[]`
- `contacts[]`
- `checklist[]`
- `notes[]`

If a field is missing, the report can still be generated. Ask a brief follow-up question only when the missing detail is important for the user's goal.

## Output behavior

The PDF includes sections for:

- overview
- flights
- hotel
- activities
- useful links
- contacts
- checklist
- notes

After running the script, tell the user the output path and summarize what the PDF contains.
