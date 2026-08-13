#!/usr/bin/env python3
"""Generate procedure_live.pdf — go-live checklist for a licensed broker."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "procedure_live.pdf"

INK = colors.HexColor("#11141b")
NAVY = colors.HexColor("#1b2433")
RULE = colors.HexColor("#c5ccd6")
ROW = colors.HexColor("#f4f6f8")
CODE_BG = colors.HexColor("#eef1f4")
MUTED = colors.HexColor("#5b6573")
WARN = colors.HexColor("#7a4a12")
WARN_BG = colors.HexColor("#fff4e0")


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    s: dict[str, ParagraphStyle] = {}
    s["cover_kicker"] = ParagraphStyle(
        "cover_kicker", parent=base["Normal"], fontName="Helvetica", fontSize=10,
        textColor=colors.HexColor("#9aa3ad"), alignment=TA_LEFT, spaceAfter=8,
    )
    s["cover_title"] = ParagraphStyle(
        "cover_title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=24,
        leading=30, textColor=colors.white, alignment=TA_LEFT, spaceAfter=10,
    )
    s["cover_sub"] = ParagraphStyle(
        "cover_sub", parent=base["Normal"], fontName="Helvetica", fontSize=11.5,
        leading=16, textColor=colors.HexColor("#d5dbe3"), alignment=TA_LEFT,
    )
    s["h1"] = ParagraphStyle(
        "h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=16,
        leading=20, textColor=NAVY, spaceBefore=16, spaceAfter=8,
    )
    s["h2"] = ParagraphStyle(
        "h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12.5,
        leading=16, textColor=INK, spaceBefore=12, spaceAfter=6,
    )
    s["body"] = ParagraphStyle(
        "body", parent=base["BodyText"], fontName="Helvetica", fontSize=9.5,
        leading=13.5, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=7,
    )
    s["cell"] = ParagraphStyle(
        "cell", parent=base["BodyText"], fontName="Helvetica", fontSize=8,
        leading=11, textColor=INK,
    )
    s["cell_h"] = ParagraphStyle(
        "cell_h", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=8,
        leading=11, textColor=colors.white,
    )
    s["bullet"] = ParagraphStyle(
        "bullet", parent=s["body"], leftIndent=14, spaceAfter=3, alignment=TA_LEFT,
    )
    s["toc"] = ParagraphStyle(
        "toc", parent=base["Normal"], fontName="Helvetica", fontSize=10,
        leading=16, textColor=NAVY, leftIndent=8,
    )
    s["warn"] = ParagraphStyle(
        "warn", parent=s["body"], textColor=WARN, backColor=WARN_BG,
        borderPadding=8, leading=13, alignment=TA_LEFT,
    )
    s["code"] = ParagraphStyle(
        "code", parent=base["Code"], fontName="Courier", fontSize=7.8,
        leading=10.5, textColor=INK, backColor=CODE_BG, leftIndent=6,
        rightIndent=6, spaceBefore=4, spaceAfter=10,
    )
    return s


S = styles()
USABLE = 7.0 * inch


class NamedDest(Flowable):
    def __init__(self, key: str, title: str | None = None, level: int = 0):
        super().__init__()
        self.key = key
        self.title = title
        self.level = level
        self.width = 0
        self.height = 0

    def draw(self) -> None:
        self.canv.bookmarkHorizontal(self.key, 0, 22)
        if self.title:
            self.canv.addOutlineEntry(self.title, self.key, self.level, closed=0)


def dest(key: str, title: str, level: int = 0) -> NamedDest:
    return NamedDest(key, title, level)


def P(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, S[style])


def toc_item(key: str, label: str) -> Paragraph:
    return P(f'<link href="#{key}" color="#1b2433"><u>{label}</u></link>', "toc")


def bullets(items: list[str]) -> list:
    return [P(f"• {item}", "bullet") for item in items]


def table(headers: list[str], rows: list[list[str]], widths: list[float]) -> Table:
    head = [Paragraph(h, S["cell_h"]) for h in headers]
    body = [[Paragraph(cell, S["cell"]) for cell in row] for row in rows]
    grid = Table([head, *body], colWidths=widths, repeatRows=1)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.35, RULE),
    ]
    for i in range(1, len(body) + 1):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i), (-1, i), ROW))
    grid.setStyle(TableStyle(cmds))
    return grid


def callout(text: str) -> Table:
    inner = Table([[P(text, "warn")]], colWidths=[USABLE])
    inner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), WARN_BG),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#e0c48a")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return inner


def header_footer(canvas, doc) -> None:
    canvas.saveState()
    w, h = letter
    if doc.page > 1:
        canvas.setFillColor(NAVY)
        canvas.rect(0, h - 28, w, 28, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(0.75 * inch, h - 18, "Market Bot  ·  Live procedure")
        canvas.drawRightString(w - 0.75 * inch, h - 18, "Not permission to go live")
        canvas.setFillColor(RULE)
        canvas.rect(0, 0, w, 32, fill=1, stroke=0)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(0.75 * inch, 14, "Not legal, tax, or financial advice")
        canvas.drawRightString(w - 0.75 * inch, 14, f"{doc.page}")
    canvas.restoreState()


def cover() -> list:
    banner = Table(
        [
            [P("MARKET BOT  ·  AUGUST 2026", "cover_kicker")],
            [P("Procedure: moving from<br/>paper to live (real money)", "cover_title")],
            [
                P(
                    "A plain-language checklist of what is missing today, what you "
                    "must decide and build, and in what order. Written for an IT "
                    "reader. This is not permission to go live.",
                    "cover_sub",
                )
            ],
        ],
        colWidths=[USABLE],
    )
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 18),
                ("RIGHTPADDING", (0, 0), (-1, -1), 18),
                ("TOPPADDING", (0, 0), (0, 0), 16),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 16),
                ("TOPPADDING", (0, 1), (-1, -1), 6),
            ]
        )
    )
    meta = table(
        ["Field", "Value"],
        [
            ["Document", "procedure_live.pdf"],
            ["Companion", "Market_Bot_Manual.pdf (how the paper desk works)"],
            ["Current mode", "Paper only. Virtual $1,000. No broker in the repo."],
            ["Live venue this bot is aimed at", "A licensed broker (typically Interactive Brokers) for listed ETFs. Crypto live is a separate product."],
            ["Document date", "13 August 2026"],
        ],
        [2.1 * inch, 4.9 * inch],
    )
    return [
        banner,
        Spacer(1, 12),
        meta,
        Spacer(1, 10),
        callout(
            "<b>Stop and read this.</b> There is no “flip a switch” in this project. "
            "Going live means writing new code that can spend real money at a broker "
            "you are allowed to use, passing their identity checks, and accepting that "
            "paper P&amp;L will not repeat. This document is not legal, tax, or "
            "financial advice. If you are unsure, stay on paper."
        ),
        Spacer(1, 14),
        P("Contents", "h1"),
        toc_item("sec-truth", "1. The honest starting point"),
        toc_item("sec-words", "2. New words (live vs paper)"),
        toc_item("sec-legal", "3. Step 0 — Are you allowed to do this?"),
        toc_item("sec-decide", "4. Step 1 — Decisions before any code"),
        toc_item("sec-account", "5. Step 2 — A real broker account"),
        toc_item("sec-build", "6. Step 3 — What you still have to build"),
        toc_item("sec-risk", "7. Step 4 — Live risk (tighter than paper)"),
        toc_item("sec-rollout", "8. Step 5 — How to turn it on without blowing up"),
        toc_item("sec-ops", "9. Step 6 — Running it"),
        toc_item("sec-checklist", "10. One-page go / no-go checklist"),
        PageBreak(),
    ]


def section_truth() -> list:
    return [
        dest("sec-truth", "1. The honest starting point"),
        P("1. The honest starting point", "h1"),
        P(
            "Today the bot is a <b>flight simulator</b>. It reads public prices "
            "(Stooq, Yahoo, Binance) and writes trades into Postgres. Nothing is "
            "sent to a broker. There is no “LIVE=true” that places an order."
        ),
        *bullets(
            [
                "<b>Paper fills are optimistic.</b> We assume we get last + a few basis points. Live, the quote can move, halt, or reject.",
                "<b>The spend-money path does not exist.</b> Someone has to write a broker adapter, order confirms, and a kill switch that cancels live orders.",
                "<b>A green paper month is not a forecast.</b> Snap and Pulse will look clever on a lucky sample.",
            ]
        ),
        P("Keep paper running as the control group. Live should be a second mode next to it, not a replacement you cannot roll back."),
    ]


def section_words() -> list:
    return [
        dest("sec-words", "2. New words (live vs paper)"),
        P("2. New words (live vs paper)", "h1"),
        table(
            ["Word", "In plain language"],
            [
                ["Paper", "Fake money in our Postgres. What you have now."],
                ["Live / prod", "Real shares bought at a licensed broker."],
                ["Broker", "The company that holds the account and sends orders to the exchange (e.g. Interactive Brokers)."],
                ["KYC", "Identity check at the broker. Passport, tax residency, questionnaires. Not optional."],
                ["PEA", "French tax wrapper for eligible EU paper. QQQ and US stocks usually do not fit. CTO is the ordinary account."],
                ["CTO", "Ordinary securities account. Can hold US ETFs. Taxed under the usual French rules if you are a French tax resident."],
                ["MiFID test", "The broker asks if you understand the product. Derivatives need extra approval. Cash ETFs are simpler."],
                ["Market data", "Live Nasdaq / Euronext quotes are often a monthly bill. Yahoo is not a licensed live feed."],
                ["Fill (live)", "The broker actually bought or sold. Not a row we invented."],
                ["Shadow mode", "Live code logs what it would send, but still does not send. Last rehearsal."],
            ],
            [1.5 * inch, 5.5 * inch],
        ),
    ]


def section_legal() -> list:
    return [
        dest("sec-legal", "3. Step 0 — Are you allowed to do this?"),
        P("3. Step 0 — Are you allowed to do this?", "h1"),
        P(
            "Listed ETFs through a licensed broker are a different world from "
            "Polymarket. In France, that path is ordinary brokerage (AMF / MiFID), "
            "not ANJ gambling — if you use a firm that is allowed to serve you, "
            "in your own name, from where you actually live."
        ),
        *bullets(
            [
                "<b>You must be allowed to open that broker account.</b> If they refuse you, stop. There is no VPS or VPN fix that is acceptable.",
                "<b>Pulse live is not the same as Slow live.</b> Buying QQQ at IBKR is not the same as trading BTC on a crypto exchange. Decide each venue separately.",
                "<b>Tax residency follows you, not the server.</b> If you remain a French tax resident, French tax can still apply to gains.",
                "<b>This PDF is not legal or tax advice.</b> If any of the above is unclear, stay on paper and talk to a professional.",
            ]
        ),
        callout(
            "If you cannot open and fund a brokerage account on the official site, "
            "in your own name, from where you live — you are not ready for this "
            "procedure. Do not treat a foreign VPS as a change of country."
        ),
    ]


def section_decide() -> list:
    return [
        dest("sec-decide", "4. Step 1 — Decisions before any code"),
        P("4. Step 1 — Decisions before any code", "h1"),
        table(
            ["Decide", "A sane first answer"],
            [
                ["Which sleeve goes live first?", "Slow only. Snap and Pulse stay paper until Slow is boring in live."],
                ["Which account?", "CTO for US ETFs. PEA only if you switch Slow to PEA-eligible EU funds."],
                ["Max live cash", "An amount a software bug can lose without ruining you."],
                ["Who holds the keys?", "You. Broker 2FA. No API secret in git."],
                ["What is the kill switch?", "Must cancel open live orders, not only stop the worker."],
            ],
            [2.4 * inch, 4.6 * inch],
        ),
    ]


def section_account() -> list:
    return [
        dest("sec-account", "5. Step 2 — A real broker account"),
        P("5. Step 2 — A real broker account", "h1"),
        P(
            "The usual multi-venue API for a solo builder is Interactive Brokers "
            "(paper account first, then live). Other brokers exist; many have no usable API."
        ),
        *bullets(
            [
                "Complete KYC and the appropriateness questionnaire honestly.",
                "Enable the paper/tws API and prove you can buy and sell 1 share of an ETF by hand from their official client.",
                "Subscribe to the market data the strategy actually needs. Yahoo is not good enough for live orders.",
                "Never put username, password, or API secrets in the repo, screenshots, or chat.",
            ]
        ),
        P("Crypto Pulse, if you ever take it live, needs a licensed crypto venue you are allowed to use. That is a second project."),
    ]


def section_build() -> list:
    return [
        dest("sec-build", "6. Step 3 — What you still have to build"),
        P("6. Step 3 — What you still have to build", "h1"),
        P("None of this is in the repo today.", "body"),
        table(
            ["Missing piece", "Why"],
            [
                ["Broker adapter", "Replace plan_buy / plan_sell with real place / cancel / fill reports."],
                ["Session clock", "No orders outside the cash session. Handle halts and half-days."],
                ["Reconcile", "Every hour: bot position must match broker position. If not, halt."],
                ["Live kill", "Kill must cancel working orders at the broker."],
                ["Shadow mode", "Same code path, log-only, for weeks before size."],
                ["Idempotent orders", "A restarted worker must not double-buy SPY."],
            ],
            [2.0 * inch, 5.0 * inch],
        ),
        P("Keep the paper desk. Add a live flag. Do not delete the simulator."),
    ]


def section_risk() -> list:
    return [
        dest("sec-risk", "7. Step 4 — Live risk (tighter than paper)"),
        P("7. Step 4 — Live risk (tighter than paper)", "h1"),
        *bullets(
            [
                "Start Slow only, at a fraction of paper size (for example 10% of what paper would buy).",
                "Keep Snap and Pulse paper until you have months of live Slow fills that match the paper blotter.",
                "Daily loss halt should be tighter than 5% on the first live weeks.",
                "Max one new live order at a time until reconcile is proven.",
                "If the broker API disconnects, flatten or hold — decide in writing before it happens.",
            ]
        ),
    ]


def section_rollout() -> list:
    return [
        dest("sec-rollout", "8. Step 5 — How to turn it on without blowing up"),
        P("8. Step 5 — How to turn it on without blowing up", "h1"),
        *bullets(
            [
                "Weeks of IBKR paper with the new adapter. Same clock as live.",
                "Shadow mode against the live account (no send).",
                "One live share of the Slow ETF, then stop and compare fill vs paper.",
                "Only then raise size. Snap / Pulse live is a later decision, each on its own.",
            ]
        ),
    ]


def section_ops() -> list:
    return [
        dest("sec-ops", "9. Step 6 — Running it"),
        P("9. Step 6 — Running it", "h1"),
        P(
            "Same Docker desk, plus a broker gateway process you must keep up. "
            "Logs must show every live order id. Backups of Postgres still matter — "
            "they are your research tape, not the official ledger. The official ledger "
            "is the broker."
        ),
    ]


def section_checklist() -> list:
    return [
        dest("sec-checklist", "10. One-page go / no-go checklist"),
        P("10. One-page go / no-go checklist", "h1"),
        table(
            ["#", "Check", "Go only if"],
            [
                ["0", "Allowed to use this broker from where you live", "Account is in your name, funded on the official site"],
                ["1", "Paper desk still running as control", "Yes"],
                ["2", "Broker adapter + cancel + reconcile written and tested", "IBKR paper matches the blotter for weeks"],
                ["3", "Secrets not in git", "Env or a secret store only"],
                ["4", "Kill cancels live orders", "You tested it"],
                ["5", "First live sleeve", "Slow only, tiny size"],
                ["6", "Tax / records", "You know how you will report"],
            ],
            [0.4 * inch, 3.2 * inch, 3.4 * inch],
        ),
        Spacer(1, 10),
        callout(
            "If any row is not a clean yes, stay on paper. "
            "Companion: Market_Bot_Manual.pdf."
        ),
    ]


def build() -> None:
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.55 * inch,
        title="Market Bot live procedure",
        author="Market Bot",
    )
    story = []
    for block in (
        cover,
        section_truth,
        section_words,
        section_legal,
        section_decide,
        section_account,
        section_build,
        section_risk,
        section_rollout,
        section_ops,
        section_checklist,
    ):
        story.extend(block())
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
