#!/usr/bin/env python3
"""Generate Market_Bot_Manual.pdf in the project root."""

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
OUT = ROOT / "Market_Bot_Manual.pdf"

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
        "cover_title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=26,
        leading=32, textColor=colors.white, alignment=TA_LEFT, spaceAfter=10,
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


def code_block(text: str) -> Preformatted:
    return Preformatted(text.strip("\n"), S["code"])


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
        canvas.drawString(0.75 * inch, h - 18, "Market Bot  ·  Paper Desk")
        canvas.drawRightString(w - 0.75 * inch, h - 18, "Paper trading only")
        canvas.setFillColor(RULE)
        canvas.rect(0, 0, w, 32, fill=1, stroke=0)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(0.75 * inch, 14, "Not financial advice  ·  No live orders")
        canvas.drawRightString(w - 0.75 * inch, 14, f"{doc.page}")
    canvas.restoreState()


def cover() -> list:
    banner = Table(
        [
            [P("TRADITIONAL MARKETS  ·  OPERATIONS GUIDE  ·  AUGUST 2026", "cover_kicker")],
            [P("Market Bot<br/>Paper Desk Manual", "cover_title")],
            [
                P(
                    "A complete picture of the bot as it is today: the paper account, "
                    "the three sleeves (Slow, Snap, Pulse), how prices are fetched, "
                    "and how to run the desk. Written for an IT reader, not a trader.",
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
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    meta = table(
        ["Field", "Value"],
        [
            ["Product", "Market Bot / Paper Desk"],
            ["Venue (paper)", "Public prices only. No broker. No exchange account."],
            ["Mode", "Paper only. Virtual $1,000. No API key, no wallet, no live order."],
            ["Slow", "Monthly dual momentum: SPY vs EZU, or cash. ~80% of the book. No stop."],
            ["Snap", "QQQ 2-day washout (RSI). ~8% of the book. ATR stop. 1–5 sessions."],
            ["Pulse", "BTC / ETH 4-hour breakout. ~12% of the book. ATR stop + trail."],
            ["UI", "http://localhost:3001"],
            ["API", "http://localhost:8002"],
            ["Document date", "13 August 2026"],
        ],
        [1.6 * inch, 5.4 * inch],
    )
    return [
        banner,
        Spacer(1, 12),
        meta,
        Spacer(1, 10),
        callout(
            "<b>Read this first.</b> The bot never sends a real order. Every fill is a "
            "simulation against a public last price plus a small fee and slippage. A "
            "green equity curve on paper is not a reason to open a broker. This is not "
            "financial advice. This project is separate from the Polymarket weather desk."
        ),
        Spacer(1, 14),
        P("Contents", "h1"),
        toc_item("sec-what", "1. What this thing is"),
        toc_item("sec-glossary", "2. Words you will see"),
        toc_item("sec-account", "3. The paper account"),
        toc_item("sec-slow", "4. Slow strategy (monthly ETFs)"),
        toc_item("sec-snap", "5. Snap strategy (aggressive QQQ)"),
        toc_item("sec-pulse", "6. Pulse strategy (crypto)"),
        toc_item("sec-data", "7. Data sources and how often they are called"),
        toc_item("sec-ui", "8. The desk (screens)"),
        toc_item("sec-ops", "9. How to run it"),
        toc_item("sec-config", "10. Settings"),
        toc_item("sec-trouble", "11. When something looks wrong"),
        toc_item("sec-limits", "12. What it will not do"),
        PageBreak(),
    ]


def section_what() -> list:
    return [
        dest("sec-what", "1. What this thing is"),
        P("1. What this thing is", "h1"),
        P(
            "This is a small program that runs on your machine in Docker. It watches "
            "public prices for two stock funds and two cryptocurrencies, applies three "
            "fixed rulebooks, and <b>pretends</b> to trade. Nothing leaves your laptop. "
            "There is no bank login and no broker."
        ),
        P(
            "Think of it as a flight simulator. The weather outside is real (live ETF "
            "and crypto prices). The plane is fake (a spreadsheet that says you have $1,000)."
        ),
        P("It keeps one ledger and three sleeves:", "body"),
        *bullets(
            [
                "<b>Slow.</b> Most of the money. US vs Europe stock baskets, once a month.",
                "<b>Snap.</b> A small, faster stock book on Nasdaq-100 (QQQ). Buys a crash-that-looks-like-a-dip, sells in a few days.",
                "<b>Pulse.</b> A small crypto book. Bitcoin and Ether, 4-hour breakouts, hard stop.",
            ]
        ),
        P(
            "A background <b>worker</b> wakes about every 30 seconds. A website at "
            "<font face='Courier'>localhost:3001</font> is the desk. Postgres stores "
            "the fake ledger. Restart Docker and the ledger is still there (unless you "
            "use <font face='Courier'>down -v</font>)."
        ),
        P(
            "Ports 3001 and 8002 were chosen so this desk can sit next to the "
            "Polymarket paper bot (3000 / 8001)."
        ),
    ]


def section_glossary() -> list:
    return [
        dest("sec-glossary", "2. Words you will see"),
        P("2. Words you will see", "h1"),
        table(
            ["Word", "In plain language"],
            [
                ["ETF", "A listed fund that holds a basket. SPY = 500 US companies. EZU = euro-area companies. QQQ = Nasdaq-100 (big tech-heavy US names)."],
                ["Sleeve", "A pocket of the same $1,000 with its own rules. Slow, Snap, Pulse."],
                ["Last / mark", "The latest public price we have. Used to value open positions."],
                ["Fill", "A simulated trade. “We bought 1.1 SPY at 772.”"],
                ["Stop", "A price under the position. If last hits it, Snap or Pulse sells. Slow has no stop."],
                ["Trail", "A stop that only moves up as the trade goes your way (Pulse)."],
                ["ATR", "Average True Range: how much this thing usually swings. Wider swing = wider stop."],
                ["RSI(2)", "A 0–100 “was this just smashed?” gauge on the last two days. Very low = washout."],
                ["SMA / average", "Simple moving average. 200-day = long-term trend. 10-month = Slow’s “is this still up?” line."],
                ["12−1", "Return from a year ago to a month ago. Last month ignored because it is noisy."],
                ["Latent", "Unrealized: (mark − buy price) × quantity. Not yet locked in. Ignores fees."],
                ["Realized", "Locked-in P&amp;L after a sell, after buy and sell fees."],
                ["Today P&amp;L", "Equity now minus equity at the start of the UTC day."],
                ["Kill switch", "Stops the worker from placing new paper trades. Does not flatten positions."],
                ["Daily halt", "If the day is down more than 5%, pause new trades until the next UTC day."],
            ],
            [1.5 * inch, 5.5 * inch],
        ),
    ]


def section_account() -> list:
    return [
        dest("sec-account", "3. The paper account"),
        P("3. The paper account", "h1"),
        P(
            "One virtual account, id = 1, starting at $1,000 cash. Equity = cash + "
            "open positions marked at last price. Today P&amp;L and latent are "
            "<b>not</b> the same number: today includes fees already paid and the "
            "move since midnight UTC; latent is only mark minus average on open lots."
        ),
        P(
            "Reset on the Control screen wipes fills, decisions, positions, and equity "
            "points, and puts $1,000 back. The <font face='Courier'>pgdata</font> Docker "
            "volume survives <font face='Courier'>compose restart</font> and "
            "<font face='Courier'>down</font>. <font face='Courier'>down -v</font> erases it."
        ),
    ]


def section_slow() -> list:
    return [
        dest("sec-slow", "4. Slow strategy (monthly ETFs)"),
        P("4. Slow strategy (monthly ETFs)", "h1"),
        P(
            "Job: stay in the stronger of two stock markets if that market is still "
            "in a long uptrend. Otherwise sit in cash. About <b>80%</b> of the book. "
            "No stop-loss. One decision per month (or on first start)."
        ),
        P("Each month the bot asks two questions:", "body"),
        *bullets(
            [
                "Is this ETF’s last <b>closed</b> US session above its ~10-month average? If no, it is not eligible.",
                "Of the eligible ones, which had the better return from 12 months ago to 1 month ago (12−1)? Hold that. If none, cash.",
            ]
        ),
        P(
            "Default names: <b>SPY</b> (S&amp;P 500) and <b>EZU</b> (euro area). "
            "It fills at the current public quote plus 2 bps slip and 5 bps fee. "
            "The <i>decision</i> uses yesterday’s close so today’s unfinished session "
            "cannot leak into the signal."
        ),
        P(
            "Judge Slow over months. A −$4 day is noise. A 5% stock stop would shake "
            "this book out of the very trend it is trying to ride."
        ),
    ]


def section_snap() -> list:
    return [
        dest("sec-snap", "5. Snap strategy (aggressive QQQ)"),
        P("5. Snap strategy (aggressive QQQ)", "h1"),
        P(
            "Job: buy a short, violent dip in Nasdaq-100 <b>only if the long trend "
            "is still up</b>, then get out in a few days. About <b>8%</b> of the book. "
            "This is the aggressive traditional sleeve — smaller and faster than Slow, "
            "stocks not crypto."
        ),
        P("Rules, in order:", "body"),
        *bullets(
            [
                "Trade only <b>QQQ</b> (Nasdaq-100 ETF).",
                "Enter on a <b>closed</b> daily bar when RSI(2) is at or below 10 (a 2-day washout) <b>and</b> price is still above the 200-day average (do not catch a falling bear market).",
                "Initial stop = entry − 2.5 × ATR(20). Checked against the live quote every 30 seconds.",
                "Exit if price closes back above the 5-day average (the bounce happened), or after 5 sessions, or if the stop is hit.",
                "Size so the stop is about 0.75% of total equity, then cap the whole sleeve at 8%.",
            ]
        ),
        P(
            "Holds are usually 1–5 trading days. Many trades will be small losers "
            "(the stop). That is the design. Do not retune Slow because Snap had a "
            "good week."
        ),
    ]


def section_pulse() -> list:
    return [
        dest("sec-pulse", "6. Pulse strategy (crypto)"),
        P("6. Pulse strategy (crypto)", "h1"),
        P(
            "Job: ride a Bitcoin or Ether push if a 4-hour bar closes at a new high, "
            "and cut if it fails. About <b>12%</b> of the book. Long only. No borrow."
        ),
        *bullets(
            [
                "Enter when a <b>finished</b> 4-hour bar closes above the prior 20-bar high.",
                "Stop = entry − 2.5 × ATR(14). Trail = close − 3 × ATR (only moves up).",
                "Also exit if a 4-hour bar closes under the prior 10-bar low.",
                "Live stop is checked every 30 seconds. New entries / trails only on a new closed 4-hour bar.",
                "After a stop, stay flat until a 4-hour close is back <b>inside</b> the channel (no re-entering the same failed breakout).",
                "Do not enter if the live price is already through the stop.",
                "Risk about 1% of total equity to the stop, then cap the sleeve at 12%.",
            ]
        ),
        P(
            "A “good” Pulse book loses often and wins fat. Long quiet periods are "
            "normal. It cannot empty Slow."
        ),
    ]


def section_data() -> list:
    return [
        dest("sec-data", "7. Data sources and how often they are called"),
        P("7. Data sources and how often they are called", "h1"),
        table(
            ["What", "Source", "How often"],
            [
                ["Worker loop", "Local", "Every 30 seconds (Control: Loop)"],
                ["SPY / EZU / QQQ history", "Stooq CSV, Yahoo 2y fallback", "First boot, then at most every 3–12 hours"],
                ["SPY / EZU / QQQ last", "Yahoo 5-day chart", "About once an hour"],
                ["BTC / ETH last", "Binance ticker", "Every 30 seconds"],
                ["BTC / ETH 4h candles", "Binance klines", "Only if we lack the last closed 4h bar"],
            ],
            [2.1 * inch, 2.4 * inch, 2.5 * inch],
        ),
        P(
            "No API keys. Binance will not run out at this rate. Yahoo is unofficial "
            "and is the only source that might briefly return 429 if hammered; the "
            "worker then keeps the last mark. The UI never calls these sites — only "
            "the worker does."
        ),
    ]


def section_ui() -> list:
    return [
        dest("sec-ui", "8. The desk (screens)"),
        P("8. The desk (screens)", "h1"),
        table(
            ["Tab", "What it is"],
            [
                ["Overview", "Equity, today, latent, realized, hit rate. Chart with Today / 7d / 30d / All. Three rails. Recent decisions and fills."],
                ["Slow", "SPY vs EZU scores and the monthly holding."],
                ["Snap", "QQQ RSI, stop, washout / bounce tape."],
                ["Pulse", "BTC / ETH channel, ATR, armed / disarmed, stop."],
                ["Trades", "Open positions first, then closed. Fills and decisions."],
                ["Analysis", "Last 20 completed trades. Notes only fire when the sample is large enough."],
                ["Control", "Start / pause / kill / reset. Sleeve sizes and stops."],
            ],
            [1.4 * inch, 5.6 * inch],
        ),
    ]


def section_ops() -> list:
    return [
        dest("sec-ops", "9. How to run it"),
        P("9. How to run it", "h1"),
        code_block(
            """cd "/Users/damien/Documents/02 - Dev/market_bot"
cp .env.example .env
docker compose up --build -d
# UI  http://localhost:3001
# API http://localhost:8002/health"""
        ),
        P(
            "Compose project name is <font face='Courier'>market_bot</font> so it "
            "does not collide with the Polymarket stack. Kill switch and daily halt "
            "are paper-only. Reset bankroll from Control."
        ),
    ]


def section_config() -> list:
    return [
        dest("sec-config", "10. Settings"),
        P("10. Settings", "h1"),
        P(
            "Defaults live in <font face='Courier'>.env</font> and in the Control "
            "page. New keys are inserted if missing; existing values are not overwritten "
            "on restart. After a Reset, Slow may buy again on the next first-run month clock."
        ),
        table(
            ["Knob", "Default", "Meaning"],
            [
                ["slow_sleeve_fraction", "0.80", "Share of equity for monthly ETFs"],
                ["snap_sleeve_fraction", "0.08", "Share of equity for QQQ"],
                ["pulse_sleeve_fraction", "0.12", "Share of equity for crypto"],
                ["snap_rsi_buy", "10", "Enter Snap when RSI(2) is at or below this"],
                ["snap_max_days", "5", "Force Snap exit after this many sessions"],
                ["pulse_stop_atr / trail", "2.5 / 3.0", "Pulse stop and trail width"],
                ["daily_loss_halt", "0.05", "Pause new trades if the UTC day is down 5%"],
                ["poll_interval_seconds", "30", "Worker wake-up. Does not change monthly / 4h clocks"],
            ],
            [2.2 * inch, 1.3 * inch, 3.5 * inch],
        ),
    ]


def section_trouble() -> list:
    return [
        dest("sec-trouble", "11. When something looks wrong"),
        P("11. When something looks wrong", "h1"),
        table(
            ["You see", "Usually means"],
            [
                ["SPY open, no stop", "Slow is working. There is no stock stop on purpose."],
                ["Pulse flat for days", "Price is inside the 20-bar high. Correct."],
                ["Snap flat for weeks", "No 2-day washout, or QQQ is under the 200-day average."],
                ["Today ≠ latent", "Fees, UTC midnight, or a closed trade. Same as the other desk."],
                ["Yahoo 429 in logs", "Quote skipped; last mark is kept. History is not pulled every 30s."],
                ["API offline on 3001", "API is 8002. Confirm compose project market_bot is up."],
            ],
            [2.2 * inch, 4.8 * inch],
        ),
    ]


def section_limits() -> list:
    return [
        dest("sec-limits", "12. What it will not do"),
        P("12. What it will not do", "h1"),
        *bullets(
            [
                "Place a live broker order. There is no Interactive Brokers (or any) adapter.",
                "Trade single stocks, futures, or raw materials. Paper ETFs and two coins only.",
                "Short Pulse or Snap. Long only.",
                "Replace a lawyer, a tax advisor, or a licensed broker.",
                "Make you eligible for any venue. That is a person-and-country question, not a server question.",
            ]
        ),
        P("Companion document: <font face='Courier'>procedure_live.pdf</font> — what going to real money would actually require."),
    ]


def build() -> None:
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.55 * inch,
        title="Market Bot Paper Desk Manual",
        author="Market Bot",
    )
    story = []
    for block in (
        cover,
        section_what,
        section_glossary,
        section_account,
        section_slow,
        section_snap,
        section_pulse,
        section_data,
        section_ui,
        section_ops,
        section_config,
        section_trouble,
        section_limits,
    ):
        story.extend(block())
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
