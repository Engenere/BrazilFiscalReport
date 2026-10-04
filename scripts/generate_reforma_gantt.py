"""Gera o cronograma (Gantt) da reforma tributária de docs/reforma-tributaria.

Uso (somente para a documentação; matplotlib NÃO é dependência da biblioteca):

    pip install matplotlib
    python scripts/generate_reforma_gantt.py

Gera docs/assets/reforma-gantt-{pt,en}-{light,dark}.png. As datas de limite legal
vêm das normas (ver docs/reforma-tributaria/research.md); as demais datas são uma
PROPOSTA de cronograma e dependem do alinhamento com os mantenedores. Para
atualizar, edite TASKS/DEADLINES abaixo e rode o script de novo.
"""

from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs" / "assets"

# kind: done | planned | optional | open (sem data definida)
# (grupo, id, nome_pt, nome_en, início, fim, kind)
TASKS = [
    (
        "danfe",
        "A1",
        "Pesquisa da NT 2026.010",
        "Research on NT 2026.010",
        date(2026, 10, 3),
        date(2026, 10, 4),
        "done",
    ),
    (
        "danfe",
        "A2",
        "Alinhamento com os mantenedores",
        "Alignment with maintainers",
        date(2026, 10, 5),
        date(2026, 10, 16),
        "planned",
    ),
    (
        "danfe",
        "A3",
        "Implementação (retrato)",
        "Implementation (portrait)",
        date(2026, 10, 19),
        date(2026, 11, 6),
        "planned",
    ),
    (
        "danfe",
        "A4",
        "Testes e PDFs de referência",
        "Tests and reference PDFs",
        date(2026, 11, 9),
        date(2026, 11, 13),
        "planned",
    ),
    (
        "danfe",
        "A5",
        "Revisão e merge",
        "Review and merge",
        date(2026, 11, 16),
        date(2026, 11, 19),
        "planned",
    ),
    (
        "danfe",
        "A6",
        "Release da biblioteca",
        "Library release",
        date(2026, 11, 20),
        date(2026, 11, 20),
        "planned",
    ),
    (
        "danfe",
        "A7",
        "Integração nos consumidores",
        "Integration in consumers",
        date(2026, 11, 23),
        date(2026, 11, 30),
        "planned",
    ),
    (
        "danfe",
        "A8",
        "Layout paisagem (opcional)",
        "Landscape layout (optional)",
        date(2026, 12, 7),
        date(2026, 12, 18),
        "optional",
    ),
    (
        "dacte",
        "B1",
        "Pesquisa: a NT 2026.004 altera o DACTE?",
        "Research: does NT 2026.004 change the DACTE?",
        date(2026, 10, 5),
        date(2026, 10, 16),
        "planned",
    ),
    (
        "dacte",
        "B2",
        "Implementação, se houver mudança",
        "Implementation, if it changes",
        date(2026, 10, 19),
        date(2026, 11, 6),
        "optional",
    ),
    (
        "dacte",
        "B3",
        "Testes e revisão",
        "Tests and review",
        date(2026, 11, 9),
        date(2026, 11, 13),
        "optional",
    ),
    (
        "danfse",
        "C1",
        "Pesquisa: NT 008 e NT 009 (DANFSe)",
        "Research: NT 008 and NT 009 (DANFSe)",
        date(2026, 10, 19),
        date(2026, 10, 30),
        "planned",
    ),
    (
        "danfse",
        "C2",
        "Implementação (sem data da NT 009)",
        "Implementation (NT 009 has no date)",
        date(2026, 11, 2),
        date(2026, 12, 31),
        "open",
    ),
    (
        "danfce",
        "D1",
        "Pesquisa: DANFCe e DANFE simplificado",
        "Research: DANFCe and simplified DANFE",
        date(2026, 10, 19),
        date(2026, 10, 30),
        "planned",
    ),
    (
        "danfce",
        "D2",
        "Acompanhar o PR #202 (DANFCe)",
        "Follow PR #202 (DANFCe)",
        date(2026, 11, 2),
        date(2026, 12, 31),
        "open",
    ),
    (
        "novos",
        "E1",
        "Pesquisa de NT de impressão (NFCom, BP-e, NF3e...)",
        "Print NT research (NFCom, BP-e, NF3e...)",
        date(2026, 11, 2),
        date(2026, 11, 13),
        "optional",
    ),
]

# (data, rótulo_pt, rótulo_en): limites legais (produção das NTs)
DEADLINES = [
    (date(2026, 11, 16), "16/11 NT 2026.004 (CT-e)", "Nov 16: NT 2026.004 (CT-e)"),
    (date(2026, 12, 1), "01/12 NT 2026.010 (DANFE)", "Dec 1: NT 2026.010 (DANFE)"),
]

GROUPS = {
    "danfe": ("DANFE NF-e (NT 2026.010)", "NF-e DANFE (NT 2026.010)"),
    "dacte": ("DACTE (NT 2026.004)", "DACTE (NT 2026.004)"),
    "danfse": ("DANFSe (NT 008 / 009)", "DANFSe (NT 008 / 009)"),
    "danfce": ("DANFCe e simplificado", "DANFCe and simplified"),
    "novos": ("Documentos novos", "New documents"),
}

PALETTES = {
    "light": {
        "bg": "#ffffff",
        "fg": "#1f2430",
        "grid": "#d9dce3",
        "done": "#2e8b57",
        "planned": "#3b6fd4",
        "optional": "#9aa3b5",
        "open": "#d9a441",
        "deadline": "#c0392b",
    },
    "dark": {
        "bg": "#1b1d24",
        "fg": "#e6e8ee",
        "grid": "#3a3e4a",
        "done": "#4cc38a",
        "planned": "#6e9bff",
        "optional": "#7b849a",
        "open": "#e0b25a",
        "deadline": "#ff6b5b",
    },
}

LABELS = {
    "pt": {
        "title": "Reforma tributária: cronograma proposto dos documentos auxiliares",
        "done": "concluído",
        "planned": "proposto",
        "optional": "condicional / opcional",
        "open": "sem data definida",
        "deadline": "limite legal (produção da NT)",
        "note": (
            "Datas de limite legal vêm das normas. "
            "As demais são proposta, sujeita aos mantenedores."
        ),
    },
    "en": {
        "title": "Tax reform: proposed schedule for the auxiliary documents",
        "done": "done",
        "planned": "proposed",
        "optional": "conditional / optional",
        "open": "no date set",
        "deadline": "legal deadline (NT in production)",
        "note": (
            "Legal deadlines come from the regulations. "
            "Other dates are a proposal, subject to maintainers."
        ),
    },
}


def draw(lang: str, theme: str) -> Path:
    pal, lab, idx = PALETTES[theme], LABELS[lang], 0 if lang == "pt" else 1
    fig, ax = plt.subplots(figsize=(13, 7.2), dpi=130)
    fig.patch.set_facecolor(pal["bg"])
    ax.set_facecolor(pal["bg"])

    rows = []
    last_group = None
    for group, tid, name_pt, name_en, start, end, kind in TASKS:
        if group != last_group:
            rows.append(("group", GROUPS[group][idx]))
            last_group = group
        rows.append(
            ("task", f"{tid}  {name_pt if lang == 'pt' else name_en}", start, end, kind)
        )

    for i, row in enumerate(rows):
        y = len(rows) - 1 - i
        if row[0] == "group":
            ax.text(
                date(2026, 9, 30),
                y,
                row[1],
                ha="right",
                va="center",
                color=pal["fg"],
                fontsize=9.5,
                fontweight="bold",
            )
            continue
        _, label, start, end, kind = row
        width = max((end - start).days + 1, 1)
        hatch = "///" if kind == "open" else None
        ax.barh(
            y,
            width,
            left=mdates.date2num(start),
            height=0.55,
            color=pal[kind],
            hatch=hatch,
            edgecolor=pal["bg"],
            linewidth=0.6,
            alpha=0.55 if kind == "open" else 1,
        )
        ax.text(
            date(2026, 9, 30),
            y,
            label,
            ha="right",
            va="center",
            color=pal["fg"],
            fontsize=8.3,
        )

    for d, text_pt, text_en in DEADLINES:
        ax.axvline(
            mdates.date2num(d),
            color=pal["deadline"],
            linewidth=1.6,
            linestyle="--",
            zorder=3,
        )
        ax.text(
            mdates.date2num(d),
            len(rows) - 0.1,
            text_pt if lang == "pt" else text_en,
            rotation=90,
            ha="right",
            va="top",
            color=pal["deadline"],
            fontsize=8.3,
            fontweight="bold",
        )

    ax.set_xlim(date(2026, 10, 1), date(2027, 1, 1))
    ax.set_ylim(-0.8, len(rows) - 0.2)
    ax.set_yticks([])
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.tick_params(axis="x", colors=pal["fg"], labelsize=8)
    ax.grid(axis="x", color=pal["grid"], linewidth=0.6)
    for spine in ax.spines.values():
        spine.set_visible(False)

    handles = [
        Patch(
            facecolor=pal[k],
            label=lab[k],
            hatch="///" if k == "open" else None,
            edgecolor=pal["bg"],
        )
        for k in ("done", "planned", "optional", "open")
    ]
    handles.append(
        plt.Line2D(
            [0], [0], color=pal["deadline"], linestyle="--", label=lab["deadline"]
        )
    )
    leg = ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.06),
        ncol=5,
        frameon=False,
        fontsize=8.3,
    )
    for text in leg.get_texts():
        text.set_color(pal["fg"])

    fig.suptitle(
        lab["title"], x=0.03, ha="left", color=pal["fg"], fontsize=13, fontweight="bold"
    )
    fig.text(0.03, 0.015, lab["note"], color=pal["fg"], fontsize=8)
    fig.subplots_adjust(left=0.36, right=0.98, top=0.9, bottom=0.14)

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"reforma-gantt-{lang}-{theme}.png"
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


if __name__ == "__main__":
    for language in ("pt", "en"):
        for color_theme in ("light", "dark"):
            print(draw(language, color_theme))
