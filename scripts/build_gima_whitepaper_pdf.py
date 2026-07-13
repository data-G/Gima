#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Flowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "GIMA_WHITEPAPER.pdf"
ASSETS = ROOT / "docs" / "assets" / "whitepaper"

PAGE_W, PAGE_H = A4
MARGIN_X = 20 * mm
MARGIN_TOP = 18 * mm
MARGIN_BOTTOM = 17 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_X

INK = colors.HexColor("#0F172A")
SLATE = colors.HexColor("#334155")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#CBD5E1")
SOFT = colors.HexColor("#F8FAFC")
NAVY = colors.HexColor("#07111F")
BLUE = colors.HexColor("#2563EB")
CYAN = colors.HexColor("#0891B2")
PURPLE = colors.HexColor("#7C3AED")
GREEN = colors.HexColor("#059669")
GOLD = colors.HexColor("#F59E0B")
RED = colors.HexColor("#DC2626")


styles = getSampleStyleSheet()
styles.add(ParagraphStyle("TitleBig", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=34, leading=38, textColor=colors.white, alignment=TA_LEFT))
styles.add(ParagraphStyle("Deck", parent=styles["BodyText"], fontName="Helvetica", fontSize=11.5, leading=16, textColor=colors.HexColor("#DBEAFE")))
styles.add(ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=23, leading=28, textColor=INK, spaceAfter=10))
styles.add(ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13.5, leading=17, textColor=SLATE, spaceBefore=8, spaceAfter=5))
styles.add(ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.6, leading=14.2, textColor=SLATE, spaceAfter=6))
styles.add(ParagraphStyle("Lead", parent=styles["BodyText"], fontName="Helvetica", fontSize=11.2, leading=16.2, textColor=SLATE, spaceAfter=8))
styles.add(ParagraphStyle("Small", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.9, leading=10.5, textColor=MUTED, spaceAfter=4))
styles.add(ParagraphStyle("HeaderSmall", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.6, leading=9.8, textColor=colors.white, spaceAfter=0))
styles.add(ParagraphStyle("Caption", parent=styles["BodyText"], fontName="Helvetica-Oblique", fontSize=7.7, leading=10.5, textColor=MUTED, alignment=TA_CENTER, spaceBefore=5))
styles.add(ParagraphStyle("Kicker", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=GOLD, spaceAfter=5))
styles.add(ParagraphStyle("CardTitle", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=INK))
styles.add(ParagraphStyle("CalloutTitle", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=INK, spaceAfter=3))
styles.add(ParagraphStyle("TOC", parent=styles["BodyText"], fontName="Helvetica", fontSize=10, leading=13, textColor=SLATE, spaceAfter=3))
styles.add(ParagraphStyle("Metric", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=18, leading=20, textColor=BLUE, alignment=TA_CENTER))
styles.add(ParagraphStyle("MetricLabel", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.4, leading=9, textColor=MUTED, alignment=TA_CENTER))


def p(text: str, style: str = "Body") -> Paragraph:
    return Paragraph(text, styles[style])


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.45)
    canvas.line(MARGIN_X, 12 * mm, PAGE_W - MARGIN_X, 12 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(MARGIN_X, 7 * mm, "Gima Whitepaper | Local-first AI workspace")
    canvas.drawRightString(PAGE_W - MARGIN_X, 7 * mm, f"Page {doc.page}")
    canvas.restoreState()


def cover_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(MARGIN_X, 7 * mm, "Gima Whitepaper | Prepared for portfolio, LinkedIn, and technical review")
    canvas.restoreState()


def styled_table(data, widths, header=True, font_size=7.8) -> Table:
    rows = []
    for row_index, row in enumerate(data):
        style = "HeaderSmall" if header and row_index == 0 else "Small"
        rows.append([Paragraph(str(cell), styles[style]) for cell in row])
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
    ]
    if header:
        commands += [
            ("BACKGROUND", (0, 0), (-1, 0), INK),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    table.setStyle(TableStyle(commands))
    return table


def callout_box(title: str, body: str, accent=BLUE) -> Table:
    table = Table(
        [[Paragraph(title, styles["CalloutTitle"])], [Paragraph(body, styles["Small"])]],
        colWidths=[CONTENT_W],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#D7E3F4")),
        ("LINEBEFORE", (0, 0), (0, -1), 3.0, accent),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def toc_table(items) -> Table:
    rows = []
    for idx, (section, description) in enumerate(items, start=1):
        rows.append([
            Paragraph(f"{idx:02d}", styles["MetricLabel"]),
            Paragraph(f"<b>{section}</b><br/><font color='#64748B'>{description}</font>", styles["TOC"]),
        ])
    table = Table(rows, colWidths=[18 * mm, CONTENT_W - 18 * mm])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.35, colors.HexColor("#E2E8F0")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2FF")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def metric_card(value: str, label: str, accent=BLUE) -> Table:
    box = Table([[Paragraph(value, styles["Metric"])], [Paragraph(label, styles["MetricLabel"])]], colWidths=[CONTENT_W / 4 - 5])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#DBEAFE")),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return box


class HeroCover(Flowable):
    def __init__(self, width, height=330):
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        c.setFillColor(NAVY)
        c.roundRect(0, 0, w, h, 18, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#0B1B33"))
        c.roundRect(12, 12, w - 24, h - 24, 15, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#102A52"))
        c.circle(w - 70, h - 78, 86, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#123C76"))
        c.circle(w - 155, 63, 58, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#1D4ED8"))
        c.roundRect(23, h - 51, 116, 22, 11, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(37, h - 43, "TECHNICAL WHITEPAPER")
        logo = ASSETS / "gima_logo_circle.png"
        if logo.exists():
            c.drawImage(ImageReader(str(logo)), w - 108, h - 116, 72, 72, mask="auto")
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 34)
        c.drawString(24, h - 98, "Gima")
        c.setFont("Helvetica-Bold", 23)
        c.drawString(24, h - 128, "Local-First AI Workspace")
        c.setFillColor(colors.HexColor("#DCEBFF"))
        c.setFont("Helvetica", 11.5)
        c.drawString(24, h - 165, "Memory, research, artifact creation, media workflows,")
        c.drawString(24, h - 184, "provider routing, image/video generation, and")
        c.drawString(24, h - 203, "review-gated self-improvement.")
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 7)
        chip_y = 72
        x = 24
        for chip in ("Inspectable", "Local-first", "Source-backed", "Human-approved", "Provider-ready"):
            tw = c.stringWidth(chip, "Helvetica-Bold", 7) + 18
            c.setFillColor(colors.HexColor("#1E3A8A"))
            c.roundRect(x, chip_y, tw, 18, 9, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.drawString(x + 9, chip_y + 6, chip)
            x += tw + 8
        c.setFillColor(colors.HexColor("#E0F2FE"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(24, 39, "Version 2.6 | 4 July 2026 | Prepared by Gimhan Gunarathne")
        c.setFillColor(colors.HexColor("#93C5FD"))
        c.setFont("Helvetica", 7.3)
        c.drawString(24, 25, "Portfolio, LinkedIn, GitHub, and technical partner presentation package")


class ArchitectureDiagram(Flowable):
    def __init__(self, width, height=175):
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        w = self.width

        def box(x, y, bw, bh, fill, title, sub, text_color=colors.white):
            c.setFillColor(fill)
            c.roundRect(x, y, bw, bh, 9, fill=1, stroke=0)
            c.setFillColor(text_color)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(x + bw / 2, y + bh / 2 + 5, title)
            c.setFont("Helvetica", 5.7)
            c.drawCentredString(x + bw / 2, y + bh / 2 - 7, sub)

        def arrow(x1, y1, x2, y2):
            c.setStrokeColor(MUTED)
            c.setLineWidth(0.8)
            c.line(x1, y1, x2, y2)
            c.setFillColor(MUTED)
            c.line(x2, y2, x2 - 4, y2 + 3)
            c.line(x2, y2, x2 - 4, y2 - 3)

        box(0, 70, 72, 36, BLUE, "User", "chat / files / tools")
        box(108, 70, 84, 36, PURPLE, "Router", "intent + risk + context")
        paths = [
            ("Brain", "local memory", colors.HexColor("#DCFCE7")),
            ("Browse", "current sources", colors.HexColor("#DBEAFE")),
            ("Artifacts", "PDF / XLSX / CSV", colors.HexColor("#FEF3C7")),
            ("Cloud", "optional teachers", colors.HexColor("#EDE9FE")),
            ("Media", "director + render", colors.HexColor("#FEE2E2")),
            ("Local model", "private fallback", colors.HexColor("#E2E8F0")),
        ]
        px, py0, bw, bh, gap = 244, 142, 95, 22, 2
        bus_x = 218
        out_x = px + bw + 24
        c.setStrokeColor(MUTED)
        c.line(bus_x, 33, bus_x, 153)
        c.line(out_x, 33, out_x, 153)
        arrow(72, 88, 108, 88)
        arrow(192, 88, bus_x, 88)
        for i, (title, sub, fill) in enumerate(paths):
            y = py0 - i * (bh + gap)
            box(px, y, bw, bh, fill, title, sub, SLATE)
            arrow(bus_x, y + bh / 2, px, y + bh / 2)
            arrow(px + bw, y + bh / 2, out_x, y + bh / 2)
        box(w - 82, 70, 82, 36, GREEN, "Answer", "reply + files + logs")
        arrow(out_x, 88, w - 82, 88)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 6.2)
        c.drawCentredString(w / 2, 7, "Routing makes Gima a workspace: every answer can carry memory, sources, generated files, and review state.")


class SafetyLoop(Flowable):
    def __init__(self, width, height=135):
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        cx = self.width / 2
        nodes = [
            ("Classify", cx - 155, 74, BLUE),
            ("Backup", cx - 54, 106, PURPLE),
            ("Test", cx + 54, 106, CYAN),
            ("Approve", cx + 155, 74, GREEN),
            ("Publish", cx + 54, 30, GOLD),
            ("Log", cx - 54, 30, SLATE),
        ]
        for title, x, y, fill in nodes:
            c.setFillColor(fill)
            c.roundRect(x - 38, y - 15, 76, 30, 8, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(x, y - 3, title)
        c.setStrokeColor(MUTED)
        c.setLineWidth(0.9)
        for a, b in [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)]:
            x1, y1 = nodes[a][1], nodes[a][2]
            x2, y2 = nodes[b][1], nodes[b][2]
            c.line(x1 + (28 if x2 > x1 else -28), y1, x2 + (-28 if x2 > x1 else 28), y2)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(cx, 68, "Human review gate")
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 7)
        c.drawCentredString(cx, 56, "No public, financial, code-sync, or identity action proceeds invisibly.")


@dataclass(frozen=True)
class ScreenshotSpec:
    path: Path
    title: str
    caption: str


def screenshot_block(spec: ScreenshotSpec) -> KeepTogether:
    img = Image(str(spec.path))
    max_w = CONTENT_W
    max_h = 111 * mm
    scale = min(max_w / img.imageWidth, max_h / img.imageHeight)
    img.drawWidth = img.imageWidth * scale
    img.drawHeight = img.imageHeight * scale
    img.hAlign = "CENTER"
    card = Table(
        [[Paragraph(spec.title, styles["CardTitle"])], [img], [Paragraph(spec.caption, styles["Caption"])]],
        colWidths=[img.drawWidth + 12],
    )
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.45, LINE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return KeepTogether([card])


def roadmap_band(items) -> Table:
    rows = []
    for phase, priority, outcome, color in items:
        rows.append([
            Paragraph(f"<b>{phase}</b><br/><font color='#64748B'>{priority}</font>", styles["Small"]),
            Paragraph(outcome, styles["Small"]),
        ])
    table = Table(rows, colWidths=[42 * mm, CONTENT_W - 42 * mm])
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]
    for idx, item in enumerate(items):
        commands.append(("BACKGROUND", (0, idx), (0, idx), item[3]))
        commands.append(("BACKGROUND", (1, idx), (1, idx), colors.white if idx % 2 == 0 else SOFT))
    table.setStyle(TableStyle(commands))
    return table


def build() -> Path:
    story = []
    story += [
        Spacer(1, 15 * mm),
        HeroCover(CONTENT_W),
        Spacer(1, 8 * mm),
        styled_table(
            [["Author", "Project", "Version", "Date"], ["Gimhan Gunarathne", "Gima / Human AI Local", "2.6", "4 July 2026"]],
            [55 * mm, 60 * mm, 25 * mm, 35 * mm],
        ),
        Spacer(1, 8 * mm),
        callout_box(
            "Whitepaper thesis",
            "Gima is positioned as an AI operations cockpit: a visible workspace for memory, research, file generation, media planning, image/video generation, provider routing, and safe self-improvement.",
            BLUE,
        ),
        Spacer(1, 7 * mm),
        p("Repository: https://github.com/data-G/Gima", "Small"),
        PageBreak(),
    ]

    story += [
        p("Contents", "H1"),
        p("This whitepaper is designed for a portfolio reader, GitHub reviewer, LinkedIn audience, or early technical partner. It separates product proof, architecture, capability status, and governance.", "Lead"),
        toc_table(
            [
                ("Executive Snapshot", "What Gima is and why it matters."),
                ("Problem and Vision", "The product gap Gima is built to solve."),
                ("System Architecture", "Router, memory, artifacts, providers, and governance."),
                ("Product Screenshots", "Current interface evidence and workflow proof."),
                ("Professional Tracks", "AI engineering, OSINT research, privacy, and full-stack capabilities."),
                ("Capability Model", "Research, reports, voice, media, code, and provider features."),
                ("Conversational Status", "Text, wake, speech, and memory states."),
                ("Safety and Governance", "Review gates and autonomy boundaries."),
                ("Criticism and Defense", "Known concerns and practical controls."),
                ("Roadmap", "Daily improvement and delivery plan."),
                ("Positioning", "LinkedIn-ready summary and references."),
            ]
        ),
        Spacer(1, 8 * mm),
        Table(
            [[metric_card("16+", "Capability tracks"), metric_card("Local", "Memory and artifacts"), metric_card("Cloud", "Optional OpenAI/OpenRouter"), metric_card("Review", "Human approval gates")]],
            colWidths=[CONTENT_W / 4] * 4,
        ),
        PageBreak(),
    ]

    story += [
        p("Executive Snapshot", "H1"),
        p("Gima turns a local machine into an inspectable AI workspace. Instead of hiding work inside a chat transcript, it routes requests through memory, browsing, deterministic artifact tools, optional cloud models, image/video generation backends, and review-gated improvement steps.", "Lead"),
        Table(
            [[metric_card("Chat", "Text, voice, and saved turns"), metric_card("Hybrid", "Local plus optional providers"), metric_card("Files", "PDF, CSV, XLSX, PNG, MP4"), metric_card("Safe", "Review before risky actions")]],
            colWidths=[CONTENT_W / 4] * 4,
        ),
        Spacer(1, 7 * mm),
        styled_table(
            [
                ["Principle", "What It Means"],
                ["Local-first memory", "Conversations, generated files, reviews, and logs are stored under the local Gima workspace."],
                ["Source-backed facts", "Current information routes through browsing or APIs instead of stale memory guesses."],
                ["Real artifacts", "Reports, source registers, screenshots, media plans, and exports are written to visible folders."],
                ["Conversational status", "Gima can chat, save conversation history, wake on a spoken name, and speak responses when the local voice backend is available."],
                ["Human-controlled improvement", "Code sync, public posting, financial actions, and self-updates require approval."],
            ],
            [48 * mm, CONTENT_W - 48 * mm],
        ),
        Spacer(1, 6 * mm),
        p("Professional thesis: useful personal AI should be auditable, multimodal, file-producing, provider-aware, and safe enough to improve continuously without becoming opaque.", "H2"),
        PageBreak(),
    ]

    story += [
        p("Professional Capability Tracks", "H1"),
        p("Gima is presented as a practical AI workspace with professional capabilities across engineering, research, privacy, and product delivery. These are capability directions backed by working modules, tests, docs, and roadmap items, not claims of full autonomous replacement.", "Lead"),
        styled_table(
            [
                ["Track", "What Gima Supports", "Proof Direction"],
                ["Gima AI Engineer", "Model routing, local-model fallback, teacher-model gateways, agent workflows, testing, evaluation, and safe self-improvement.", "Provider fallback tests, upgrade reports, capability dashboard, review-gated code changes"],
                ["OSINT Research Architect", "Source-backed public research, authorized research gates, citation registers, contradiction notes, research dossiers, and exportable evidence tables.", "Source registers, cited reports, authorization gate, uncertainty flags, public-source exports"],
                ["Privacy Engineer", "Local-first memory, masked secrets, permission checks, cloud-use gating, provenance manifests, protected paths, and review queues.", "CLOUD_ALLOWED gate, masked API keys, protected downloads, local memory paths"],
                ["Full-Stack AI Builder", "Python backend, browser UI, local files, artifact generation, API integrations, GitHub/deployment workflows, and user-facing product documentation.", "Working web app, generated files, tested routes, GitHub sync docs, deployment guides"],
            ],
            [36 * mm, 78 * mm, CONTENT_W - 114 * mm],
        ),
        Spacer(1, 7 * mm),
        callout_box(
            "Positioning rule",
            "Use these tracks for portfolio, sponsor, and LinkedIn communication, but keep language evidence-based: Gima assists, drafts, routes, tests, and documents. Public, financial, identity, and cloud actions remain user-approved.",
            CYAN,
        ),
        PageBreak(),
    ]

    story += [
        p("Problem and Product Vision", "H1"),
        p("Most AI assistants are powerful but opaque: users cannot always see which model answered, whether a current fact was checked, where files were saved, or what would happen if the system modified itself. Gima addresses this by treating AI as a workspace rather than a single chat box.", "Body"),
        styled_table(
            [
                ["Need", "Gima Response"],
                ["Trust", "Show sources, files, provider status, and memory paths."],
                ["Speed", "Use small local routes for quick fallback and stronger providers when needed."],
                ["Professional output", "Generate reports, costings, screenshots, PDFs, and structured exports."],
                ["Conversation", "Support text chat, wake-word activation, spoken responses, and local voice conversation logs."],
                ["Media creation", "Plan scenes, camera angles, emotions, audio timing, and backend render steps."],
                ["Growth", "Prepare legal earning assets while keeping public, financial, and identity actions user-approved."],
            ],
            [48 * mm, CONTENT_W - 48 * mm],
        ),
        Spacer(1, 7 * mm),
        p("Target experience: the user asks for a business report, web research, media plan, code change, or GitHub sync. Gima chooses the correct route, creates visible outputs, logs the result, and asks for approval when risk increases.", "Body"),
        PageBreak(),
    ]

    story += [
        p("System Architecture", "H1"),
        p("Gima is organized around a router. Each request is classified by intent, risk, and context, then sent to memory, browsing, artifact generation, cloud models, local fallback, or media workflows.", "Body"),
        p("Figure 1 - Gima Routing Architecture", "H2"),
        ArchitectureDiagram(CONTENT_W),
        Spacer(1, 7 * mm),
        styled_table(
            [
                ["Layer", "Responsibility", "Implementation"],
                ["Interface", "Chat, uploads, dashboards, tool buttons", "human_ai/web_ui.py"],
                ["Memory", "Records, reviews, brain index, source files", ".human-ai, memory.py, brain_index.py"],
                ["Routing", "Select brain, browse, artifact, media, cloud, or local path", "agent.py, artifacts.py, services.py"],
                ["Providers", "Optional OpenAI, Gemini, Anthropic, OpenRouter routes", "services.py, config"],
                ["Artifacts", "PDF, CSV, Markdown, images, video manifests", "hands/out, scripts"],
                ["Governance", "Secrets, approval gates, quotas, sync checks", "secrets.py, quota.py, self_update.py"],
            ],
            [30 * mm, 75 * mm, CONTENT_W - 105 * mm],
        ),
        PageBreak(),
    ]

    screenshots = [
        ScreenshotSpec(ASSETS / "artifact_report_workflow.jpg", "Artifact and Report Workflow", "Gima recognizes a table/report request and returns saved CSV/PDF style outputs instead of only a chat answer."),
        ScreenshotSpec(ASSETS / "chat_workspace_tools.jpg", "Chat Workspace and Tool Controls", "The interface exposes copy/export controls, feature buttons, memory/provider state, and workspace navigation."),
        ScreenshotSpec(ASSETS / "media_workflow_controls.jpg", "Media and Lip-Sync Workflow Controls", "The product direction includes uploaded image/audio workflows, director planning, and lip-sync/rendering routes."),
    ]
    story += [p("Product Screenshots", "H1"), p("The screenshots below are included as product evidence. They show the current Gima workspace UI, generated-output behavior, and early multimodal controls.", "Body")]
    story += [screenshot_block(screenshots[0]), PageBreak()]
    story += [p("Product Screenshots", "H1"), screenshot_block(screenshots[1]), PageBreak()]
    story += [p("Product Screenshots", "H1"), screenshot_block(screenshots[2]), PageBreak()]

    story += [
        p("Capability Model", "H1"),
        styled_table(
            [
                ["Capability", "Current / Planned Behavior", "Professional Output"],
                ["Research", "Browse or import public sources, summarize, and save source metadata.", "Cited notes, CSV registers, PDF briefings"],
                ["Authorized security audit", "Ask ownership, permission, scope, allowed/prohibited actions, and private-report preference before security or reverse-engineering-style work.", "Private responsible report, safe public-only fallback"],
                ["Costing and tables", "Build assumption-led estimates and export visible files.", "Excel-style workbooks, JPG previews, PDFs"],
                ["Conversational AI", "Hold text conversations, save history, wake on spoken Gima, and speak replies where voice tools are available.", "Conversation CSV, voice turns, wake events"],
                ["Provider routing", "Use local fallback or optional cloud models based on task difficulty.", "Provider-aware answer logs"],
                ["Image generation", "Generate ChatGPT/OpenAI images from prompts with consent and local provenance manifests.", "PNG output, prompt file, manifest"],
                ["Veo video generation", "Submit OpenRouter/Veo cloud video jobs, poll status, download MP4, and save usage/cost metadata.", "MP4 output, job ID, manifest"],
                ["Media director", "Analyze prompt/audio, create scenes, camera moves, emotion map, and render plan.", "Shot list, storyboard, timing manifest"],
                ["GitHub sync", "Check CLI auth, scan for obvious secrets, commit, push, and open draft PR.", "Reviewable branch and PR"],
                ["Agent workbench", "Plan-act-observe loops with logs and human checkpoints.", "Resumable task ledger"],
            ],
            [40 * mm, 78 * mm, CONTENT_W - 118 * mm],
        ),
        Spacer(1, 7 * mm),
        p("The strongest near-term product advantage is not claiming frontier autonomy. It is proving reliable workflow conversion: prompt to route, route to file, file to review, review to improvement.", "Body"),
        PageBreak(),
    ]

    story += [
        p("Conversational Status", "H1"),
        p("Gima is conversational first. The user should be able to type, speak, ask follow-up questions, and see whether Gima is listening, thinking, speaking, saving memory, or waiting.", "Body"),
        styled_table(
            [
                ["Area", "Status", "Implementation / Evidence"],
                ["Text chat", "Working", "Web UI chat sends turns through Gima and saves conversations locally."],
                ["Conversation memory", "Working", "MemoryStore writes user and assistant turns into searchable conversation CSV files."],
                ["Wake word", "Working / tested", "WakeAssistant detects Gima and aliases while avoiding word-fragment false matches."],
                ["Speak replies", "Working where backend is available", "Voice().speak(...) is used in wake and assistant flows."],
                ["Direct voice conversation", "Started", "LocalAssistant.run_conversation(...) supports turn-taking, cleanup of filler transcripts, and stop phrases."],
                ["Multilingual speech normalization", "Started", "Unicode-preserving normalization supports mixed-language transcripts."],
                ["Realtime browser voice UI", "Planned", "Add microphone controls, live transcription, streaming speech, interruption, and visible status states."],
            ],
            [40 * mm, 42 * mm, CONTENT_W - 82 * mm],
        ),
        Spacer(1, 7 * mm),
        styled_table(
            [
                ["Status State", "Meaning"],
                ["Listening", "Microphone or wake-word flow is active with user permission."],
                ["Thinking", "Gima is routing the request through memory, model, tool, browse, or artifact flow."],
                ["Speaking", "A local or configured voice backend is reading the reply aloud."],
                ["Saving memory", "The transcript and response are being written to local conversation history."],
                ["Waiting", "Gima is idle and ready for the next typed or spoken turn."],
            ],
            [48 * mm, CONTENT_W - 48 * mm],
        ),
        Spacer(1, 6 * mm),
        p("Voice must remain user-controlled: no silent recording, clear microphone permission, optional speech output, and an immediate stop phrase such as end game.", "H2"),
        PageBreak(),
    ]

    story += [
        p("Safety and Governance", "H1"),
        p("Gima uses application controls in addition to prompts. This keeps learning, code changes, publishing, and money-related workflows visible and reviewable.", "Body"),
        SafetyLoop(CONTENT_W),
        Spacer(1, 7 * mm),
        styled_table(
            [
                ["Risk", "Control"],
                ["API key exposure", "Masked UI, local secrets files, Git ignore rules, and pre-sync secret scans."],
                ["Fake current facts", "Route current information through browsing or APIs."],
                ["Unsafe automation", "Require approval for GitHub sync, public posts, financial actions, and purchases."],
                ["Media misuse", "Require consent gates and provenance manifests for image/audio/video workflows."],
                ["Bad self-improvement", "Use backup, patch, test, review, and rollback paths instead of silent live mutation."],
            ],
            [50 * mm, CONTENT_W - 50 * mm],
        ),
        PageBreak(),
    ]

    story += [
        p("Criticism and Defense Matrix", "H1"),
        p("The whitepaper deliberately avoids claiming unchecked autonomy. Gima is strongest when positioned as a review-gated workspace that can produce visible outputs, tests, logs, and rollback paths.", "Lead"),
        styled_table(
            [
                ["Potential criticism", "Why it matters", "Defense built into Gima"],
                ["Not fully autonomous", "Gima should not claim complete unsupervised autonomy.", "Frame autonomy as scoped, logged, reversible, and approval-gated for spending, posting, deployment, client contact, and live self-editing."],
                ["Evaluation still needed", "Architecture claims require benchmark evidence.", "Publish benchmark prompts, metrics, output samples, failure cases, and regression tests."],
                ["Local storage can still leak", "Local-first does not automatically mean secure.", "Use masked keys, secret scanning, permissioning, backups, recovery tests, and an encryption roadmap."],
                ["RAG can still be wrong", "Source-backed answers can misread sources.", "Add contradiction notes, citation validation, quote boundaries, uncertainty flags, and source freshness checks."],
                ["Artifact tools can fail", "Files may generate with formatting, schema, formula, or rendering errors.", "Use open-file checks, visual QA, schema checks, manifests, and repair loops."],
                ["Self-improvement can regress", "Code changes may break the system.", "Require backup, isolated copy, tests, diff review, rollback path, and release notes before sync."],
            ],
            [40 * mm, 48 * mm, CONTENT_W - 88 * mm],
        ),
        Spacer(1, 8 * mm),
        callout_box(
            "Positioning rule",
            "Gima should be presented as practical, inspectable, and improving - not as a magic autonomous agent. Its credibility comes from outputs, controls, and tests.",
            GREEN,
        ),
        PageBreak(),
    ]

    story += [
        p("Roadmap", "H1"),
        roadmap_band(
            [
                ("Reliability", "P0", "Stable startup, health checks, provider status, clean restart behavior.", colors.HexColor("#DBEAFE")),
                ("Conversation", "P0", "Visible listening/thinking/speaking/saving states, voice controls, and conversation memory quality checks.", colors.HexColor("#D1FAE5")),
                ("Research", "P0", "Cited research dossiers, source registers, and contradiction notes.", colors.HexColor("#E0F2FE")),
                ("Artifacts", "P0", "Professional Excel/PDF/JPG workflows with assumptions and manifests.", colors.HexColor("#FEF3C7")),
                ("Provider Layer", "P1", "OpenRouter model picker, MiniMax tests, streaming, usage and cost logs.", colors.HexColor("#EDE9FE")),
                ("Media", "P1", "True video backend adapters, scene planner, audio analysis, lip-sync evaluation.", colors.HexColor("#FEE2E2")),
                ("Agents", "P2", "Resumable plan-act-observe workbench with progress UI and completion tests.", colors.HexColor("#DCFCE7")),
                ("Public Release", "P2", "License, GitHub release, demo video, LinkedIn launch, whitepaper package.", colors.HexColor("#F1F5F9")),
            ]
        ),
        Spacer(1, 8 * mm),
        p("Daily Improvement Loop", "H2"),
        styled_table(
            [
                ["Track", "Daily Evidence"],
                ["Reliability", "Status, startup, hidden errors, and smoke tests."],
                ["Knowledge", "Source-backed learning and brain rebuild."],
                ["Artifact", "One real output bundle."],
                ["Legal earning", "A truthful portfolio, proposal, or LinkedIn asset."],
                ["Evaluation", "Focused tests or live product checks."],
                ["Safe self-improvement", "Backup, diff, tests, and approval."],
            ],
            [45 * mm, CONTENT_W - 45 * mm],
        ),
        PageBreak(),
    ]

    story += [
        p("LinkedIn-Ready Positioning", "H1"),
        p("I am building Gima, a local-first AI workspace that combines private memory, web browsing, real artifact generation, optional cloud models, media planning, and safe self-improvement.", "Body"),
        p("The idea is simple: a useful personal AI should not only chat. It should remember locally, browse when facts are current, create real files, show sources, protect secrets, and improve through tests and user approval.", "Body"),
        p("Gima is still experimental, but it is becoming a practical AI workspace for research, reports, media planning, coding, GitHub sync, and daily improvement.", "Body"),
        Spacer(1, 8 * mm),
        p("Conclusion", "H1"),
        p("Gima's value is not one model. Its value is the system around the model: local memory, source-backed browsing, deterministic artifact routes, optional cloud intelligence, visible files, safety controls, tests, and user approval.", "Body"),
        Spacer(1, 6 * mm),
        styled_table(
            [
                ["Reference", "URL"],
                ["Local-first software", "https://www.inkandswitch.com/essay/local-first/"],
                ["Retrieval-Augmented Generation", "https://arxiv.org/abs/2005.11401"],
                ["OWASP GenAI Security Project", "https://genai.owasp.org/"],
                ["NIST AI Risk Management Framework", "https://www.nist.gov/itl/ai-risk-management-framework"],
                ["OpenRouter Documentation", "https://openrouter.ai/docs"],
                ["Gima source repository", "https://github.com/data-G/Gima"],
            ],
            [55 * mm, CONTENT_W - 55 * mm],
        ),
    ]

    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        rightMargin=MARGIN_X,
        leftMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title="Gima Whitepaper",
        author="Gimhan Gunarathne",
        subject="Local-first AI workspace",
    )
    doc.build(story, onFirstPage=cover_footer, onLaterPages=footer)
    return OUT


if __name__ == "__main__":
    print(build())
