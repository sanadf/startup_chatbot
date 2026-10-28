"""Generate investment PDFs from existing ArabiAgent reports."""
from datetime import datetime, timezone
from html import escape
from io import BytesIO
from urllib.parse import urlparse

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)


def build_investment_pdf(report: dict) -> bytes:
    if not isinstance(report, dict):
        raise TypeError("Report must be a dictionary")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=20*mm, bottomMargin=20*mm
    )

    sheet = getSampleStyleSheet()
    sheet.add(ParagraphStyle(
        name="InvestmentTitle",
        parent=sheet["Title"],
        textColor=colors.HexColor("#183153"),
        fontSize=20
    ))
    sheet.add(ParagraphStyle(
        name="InvestmentSection",
        parent=sheet["Heading2"],
        textColor=colors.HexColor("#183153"),
        spaceBefore=13
    ))
    sheet.add(ParagraphStyle(
        name="InvestmentSmall",
        parent=sheet["BodyText"],
        fontSize=8,
        leading=11
    ))

    def para(value, style="BodyText"):
        text = str(value if value is not None else "Not verified")
        return Paragraph(escape(text), sheet[style])

    def link(url):
        if not isinstance(url, str):
            return None
        parsed = urlparse(url)
        if parsed.scheme not in ("https", "http") or not parsed.netloc:
            return None
        safe_url = escape(url, quote=True)
        return Paragraph(
            f'<link href="{safe_url}" color="blue">View source</link>',
            sheet["InvestmentSmall"]
        )

    results = report.get("results", [])
    results = results if isinstance(results, list) else []

    good = sum(
        not r.get("error")
        for r in results if isinstance(r, dict)
    )
    matches = sum(
        r.get("stage_status") == "match"
        for r in results if isinstance(r, dict)
    )

    story = [
        para("ArabiAgent Investment Report", "InvestmentTitle"),
        Spacer(1, 8),
        para("Investment thesis", "InvestmentSection"),
        para(report.get("thesis", "Not specified")),
        Spacer(1, 8),
        para(
            f"Generated {datetime.now(timezone.utc):%d %b %Y} (UTC)",
            "InvestmentSmall"
        ),
        para("Executive summary", "InvestmentSection"),
        para(
            f"{len(results)} startups researched | "
            f"{good} profiles completed | "
            f"{matches} reported funding-stage matches"
        ),
        para("Company comparison", "InvestmentSection"),
    ]

    rows = [[
        para(x, "InvestmentSmall")
        for x in ("Company", "Funding stage", "Match", "Research")
    ]]

    for item in results:
        if not isinstance(item, dict):
            continue

        company = item.get("company") or {}

        rows.append([
            para(company.get("name", "Unknown"), "InvestmentSmall"),
            para(company.get("funding_stage", "Unknown"), "InvestmentSmall"),
            para(
                str(item.get("stage_status", "unverified")).replace("_", " "),
                "InvestmentSmall"
            ),
            para(
                "Failed" if item.get("error") else "Complete",
                "InvestmentSmall"
            ),
        ])

    if len(rows) == 1:
        rows.append([para("No startups found"), "", "", ""])

    table = Table(
        rows,
        colWidths=[58*mm, 47*mm, 40*mm, 29*mm],
        repeatRows=1
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0),
         colors.HexColor("#EDF2F8")),
        ("LINEBELOW", (0, 0), (-1, -1),
         0.3, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
    ]))

    story += [
        table,
        para("Startup profiles and evidence", "InvestmentSection")
    ]

    for number, item in enumerate(results, 1):
        if not isinstance(item, dict):
            continue

        company = item.get("company") or {}

        story += [
            para(
                f"{number}. {company.get('name', 'Unknown')}",
                "InvestmentSection"
            ),
            para(company.get("description", "No description"))
        ]

        if item.get("stage_reason"):
            story.append(
                para(f"Funding match: {item['stage_reason']}")
            )

        if item.get("error"):
            story.append(
                para(f"Research issue: {item['error']}")
            )

        for field in ("website", "source_url"):
            source = link(company.get(field))
            if source:
                story.append(source)

        review = item.get("analyst_review") or {}

        if isinstance(review, dict) and review:
            story.append(
                para("CrewAI analyst review", "InvestmentSection")
            )

            if review.get("summary"):
                story.append(para(review["summary"]))

            for risk in review.get("red_flags", []) or []:
                story.append(
                    para(f"Risk / evidence gap: {risk}")
                )

            for question in review.get(
                "follow_up_questions", []
            ) or []:
                story.append(
                    para(f"Due diligence question: {question}")
                )

        for fact in item.get("attributes", []) or []:
            if not isinstance(fact, dict):
                continue

            story.append(para(
                f"{fact.get('name', 'Attribute')}: "
                f"{fact.get('value', 'Not verified')}"
            ))

            source = link(fact.get("source_url"))
            if source:
                story.append(source)

        story.append(Spacer(1, 6))

    story += [
        Spacer(1, 12),
        para(
            "Disclaimer: Based on public sources and AI analysis. "
            "Independently verify funding and financial claims "
            "before investing.",
            "InvestmentSmall"
        )
    ]

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(
            18*mm, 12*mm,
            "ArabiAgent | Investment Research"
        )
        canvas.drawRightString(
            A4[0]-18*mm, 12*mm,
            f"Page {document.page}"
        )
        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=footer,
        onLaterPages=footer
    )

    return buffer.getvalue()
