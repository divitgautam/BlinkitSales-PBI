"""Shared chart style for the BlinkitSales analysis notebooks.

House rules (D:\\Wolf\\PBI\\_knowledge\\dataviz_playbook.md): brand palette for categories (Blinkit green / yellow plus
neutrals), ColorBrewer sequential (YlGn) for magnitudes, colourblind-safe diverging (RdBu / PuOr) for variances,
action titles that state the finding, a source/caveat footnote, direct labels, zero baselines for bars, intervals
where the chart is inferential, no chart junk. One figure width (11 in) and 160 dpi for every PNG.

    from viz_style import *
    fig, ax = new_fig(h=4.8); ...; headline(fig, "Finding as a sentence", "what is plotted"); footnote(fig, "Source ..."); save(fig, "eda/name")
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DPI, WIDTH = 160, 11.0

# ---------------------------------------------------------------- palettes
GREEN, YELLOW = "#0C831F", "#F8CB46"
DKGREEN, MIDGREEN, LTGREEN = "#0A3D1F", "#5FA96B", "#CFE8D4"
INK, MUTED, GRID, GREY, LTGREY = "#1F2A24", "#5B6760", "#E3E8E1", "#9AA59E", "#CDD3CE"
ALERT = "#C0392B"                       # used sparingly, always with a label or sign
CAT = [GREEN, YELLOW, DKGREEN, GREY, MIDGREEN, "#B98300"]     # at most six hues, same order everywhere

try:                                    # ColorBrewer helper from the shared knowledge folder, with inline fallbacks
    sys.path.insert(0, r"D:\Wolf\PBI\_knowledge")
    import colorbrewer as cb
    _YLGN, _RDBU, _PUOR = cb.get("YlGn", 9), cb.get("RdBu", 11), cb.get("PuOr", 11)
except Exception:                       # pragma: no cover
    _YLGN = ['#ffffe5', '#f7fcb9', '#d9f0a3', '#addd8e', '#78c679', '#41ab5d', '#238443', '#006837', '#004529']
    _RDBU = ['#67001f', '#b2182b', '#d6604d', '#f4a582', '#fddbc7', '#f7f7f7', '#d1e5f0', '#92c5de', '#4393c3', '#2166ac', '#053061']
    _PUOR = ['#7f3b08', '#b35806', '#e08214', '#fdb863', '#fee0b6', '#f7f7f7', '#d8daeb', '#b2abd2', '#8073ac', '#542788', '#2d004b']
SEQ = ListedColormap(_YLGN, name="YlGn9")                       # magnitudes
SEQ_LIGHT = LinearSegmentedColormap.from_list("seq_light", _YLGN[:7])
DIV = LinearSegmentedColormap.from_list("RdBu11", _RDBU)        # variances: red below, blue above the midpoint
DIV2 = LinearSegmentedColormap.from_list("PuOr11", _PUOR[::-1])  # alternative: orange below, purple above
BAD, GOOD = _RDBU[2], _RDBU[8]                                  # colourblind-safe negative / positive


def setup():
    sns.set_theme(style="white", context="notebook", font="DejaVu Sans", rc={
        "figure.dpi": 100, "savefig.dpi": DPI, "figure.facecolor": "white", "axes.facecolor": "white",
        "axes.edgecolor": LTGREY, "axes.labelcolor": MUTED, "axes.titlesize": 10, "axes.titleweight": "regular",
        "axes.titlelocation": "left", "axes.labelsize": 9, "xtick.color": MUTED, "ytick.color": MUTED,
        "xtick.labelsize": 8.5, "ytick.labelsize": 8.5, "text.color": INK, "axes.spines.top": False,
        "axes.spines.right": False, "axes.grid": False, "legend.frameon": False, "legend.fontsize": 8.5,
        "axes.prop_cycle": matplotlib.cycler(color=CAT), "font.size": 9})


setup()


# ---------------------------------------------------------------- figure scaffolding
def new_fig(h=4.8, nrows=1, ncols=1, w=WIDTH, left=0.08, pad=0.0, **kw):
    """Fixed-width figure; plot area is h inches tall, plus 1.4 in for the headline and 0.65 in for the footnote."""
    H = h + 2.05 + pad          # pad: extra inches below the axes for rotated tick labels
    fig, ax = plt.subplots(nrows, ncols, figsize=(w, H), **kw)
    fig.subplots_adjust(top=1 - 1.4 / H, bottom=(0.65 + pad) / H + 0.03, left=left, right=0.97)
    return fig, ax


def headline(fig, title, sub=None):
    """Action title (the finding as a sentence, wrapped to two lines at most) and a one-line description of what is plotted."""
    import textwrap
    H = fig.get_figheight()
    lines = textwrap.wrap(title, 88)[:2]
    fig.text(0.015, 1 - 0.12 / H, chr(10).join(lines), ha="left", va="top", fontsize=13.5, fontweight="bold", color=INK, linespacing=1.25)
    if sub:
        sub = chr(10).join(textwrap.wrap(sub, 170)[:2])
        fig.text(0.015, 1 - (0.12 + 0.27 * len(lines) + 0.12) / H, sub, ha="left", va="top", fontsize=9, color=MUTED, linespacing=1.3)


def footnote(fig, text):
    import textwrap
    fig.text(0.015, 0.012, chr(10).join(textwrap.wrap(text, 205)[:3]), ha="left", va="bottom", fontsize=7.4, color=MUTED, linespacing=1.3)


def save(fig, rel, tight=False):
    """rel like 'eda/audit_quality' -> docs/eda/audit_quality.png (160 dpi)."""
    p = DOCS / f"{rel}.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=DPI, facecolor="white")
    plt.close(fig)
    return p


def clean_axes(ax, grid="y"):
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=0)
    if grid:
        ax.grid(axis=grid, color=GRID, lw=0.8)
        ax.set_axisbelow(True)
    return ax


# ---------------------------------------------------------------- formatting
def inr(v, unit=None, d=2):
    """Rupee amount in lakh / crore: inr(1.1e7) -> '₹1.10 Cr'."""
    if unit is None:
        unit = "Cr" if abs(v) >= 1e7 else ("L" if abs(v) >= 1e5 else "")
    div = {"Cr": 1e7, "L": 1e5, "": 1}[unit]
    return f"₹{v / div:,.{d if unit else 0}f}" + (f" {unit}" if unit else "")


def pct(v, d=1, sign=False):
    return f"{v * 100:+.{d}f}%" if sign else f"{v * 100:.{d}f}%"


def pfmt(p):
    return "p < 0.001" if p < 0.001 else f"p = {p:.2f}" if p >= 0.01 else f"p = {p:.3f}"


# ---------------------------------------------------------------- statistics helpers
def wilson(k, n, z=1.96):
    """Wilson score interval for a proportion k/n (vectorised)."""
    k, n = np.asarray(k, float), np.asarray(n, float)
    p = k / n
    den = 1 + z ** 2 / n
    c = (p + z ** 2 / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
    return c - h, c + h


def boot_ci(x, f=np.mean, n=2000, seed=7, q=(2.5, 97.5)):
    rng = np.random.default_rng(seed)
    x = np.asarray(x)
    v = [f(x[rng.integers(0, len(x), len(x))]) for _ in range(n)]
    return tuple(np.percentile(v, q))


# ---------------------------------------------------------------- reusable chart parts
def bar_h(ax, labels, values, color=GREEN, highlight=None, fmt=lambda v: f"{v:,.0f}", xerr=None, fs=8.5, zero=True):
    """Sorted horizontal bar with direct value labels (labels left, no legend). highlight: index list in accent."""
    y = np.arange(len(labels))
    cols = [color] * len(labels)
    for i in (highlight or []):
        cols[i] = YELLOW
    ax.barh(y, values, color=cols, height=0.68)
    if xerr is not None:
        ax.errorbar(values, y, xerr=xerr, fmt="none", ecolor=INK, elinewidth=1, capsize=2.5)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    hi = np.max(values if xerr is None else np.asarray(values) + np.asarray(xerr)[1] if np.ndim(xerr) == 2 else values)
    for yi, v in zip(y, values):
        e = 0
        if xerr is not None and np.ndim(xerr) == 2:
            e = xerr[1][yi]
        ax.text(v + e + hi * 0.012, yi, fmt(v), va="center", fontsize=fs, color=INK)
    if zero:
        ax.set_xlim(0, hi * 1.18)
    ax.xaxis.set_visible(False)
    ax.spines[["bottom", "left", "top", "right"]].set_visible(False)
    ax.tick_params(length=0)
    return ax


def waterfall(ax, labels, values, start_label=None, start=None, end_label=None, fmt=lambda v: f"{v:+,.0f}",
              total_fmt=lambda v: f"{v:,.0f}", err=None, ylim=None, fs=8.5):
    """Waterfall: optional start total, signed steps, optional end total. err: list of (lo, hi) per step, absolute values
    relative to the running total before the step (drawn as whiskers). Increases blue, decreases red-orange (colourblind-safe pair),
    totals green; every step is labelled with its sign. Axis limits are fitted to bars and whiskers unless ylim is given."""
    cum, x, labs, ext = 0.0, 0, [], [0.0]
    lab_kw = dict(ha="center", fontsize=fs, bbox=dict(fc="white", ec="none", pad=1.2, alpha=.85), zorder=5)
    if start is not None:
        ax.bar(x, start, color=GREEN, width=0.62)
        ax.text(x, start, total_fmt(start), va="bottom", fontweight="bold", **lab_kw)
        cum = start; ext.append(start)
        labs.append(start_label or "Start"); x += 1
    for i, v in enumerate(values):
        ax.bar(x, v, bottom=cum, color=GOOD if v >= 0 else BAD, width=0.62)
        ext += [cum, cum + v]
        if err is not None and err[i] is not None:
            lo, hi = err[i]
            ax.plot([x, x], [cum + lo, cum + hi], color=INK, lw=1, zorder=4)
            for yy in (cum + lo, cum + hi):
                ax.plot([x - 0.08, x + 0.08], [yy, yy], color=INK, lw=1, zorder=4)
            ext += [cum + lo, cum + hi]
        ax.text(x, cum + max(v, 0), fmt(v), va="bottom", **lab_kw)
        ax.plot([x - 0.31, x + 0.69], [cum + v, cum + v], color=LTGREY, lw=0.8, zorder=0)
        cum += v; labs.append(labels[i]); x += 1
    if end_label is not None:
        # a change total is coloured by its sign (a negative change in brand green reads as good news)
        ax.bar(x, cum, color=(GOOD if cum >= 0 else BAD) if start is None else GREEN, width=0.62)
        ext.append(cum)
        ax.text(x, cum + max(cum, 0) * 0, total_fmt(cum), va="bottom" if cum >= 0 else "top", fontweight="bold", **lab_kw)
        labs.append(end_label); x += 1
    ax.set_xticks(range(x), labs)
    ax.tick_params(length=0)
    ax.spines[["left", "top", "right"]].set_visible(False)
    ax.yaxis.set_visible(False)
    lo, hi = min(ext), max(ext)
    m = (hi - lo) * 0.14
    ax.set_ylim(*(ylim or (lo - m if lo < 0 else 0, hi + m)))
    return ax


def heat(ax, data, fmt="{:.0f}", cmap=SEQ_LIGHT, center=None, vmin=None, vmax=None, annot=True, cbar_label=None,
         xlabels=None, ylabels=None, fs=8, mask=None, cbar=True):
    """Annotated heatmap through seaborn; center=0 style for diverging (midpoint white)."""
    ann = data.map(lambda v: "" if pd.isna(v) else fmt.format(v)) if annot else False
    sns.heatmap(data, ax=ax, cmap=cmap, center=center, vmin=vmin, vmax=vmax, annot=ann, fmt="", annot_kws={"fontsize": fs},
                linewidths=0.6, linecolor="white", cbar=cbar, mask=mask,
                cbar_kws={"shrink": 0.7, "label": cbar_label} if cbar else None)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.tick_params(length=0)
    if xlabels is not None:
        ax.set_xticklabels(xlabels)
    if ylabels is not None:
        ax.set_yticklabels(ylabels, rotation=0)
    return ax


def note(ax, x, y, text, **kw):
    """Annotation in data coordinates, muted, no arrow clutter."""
    kw.setdefault("fontsize", 8.5)
    kw.setdefault("color", INK)
    return ax.text(x, y, text, **kw)


def blank_fig(h=6.0, pad=0.0, left=0.08, w=WIDTH):
    """Figure with the standard margins and no axes; build a layout with grid(fig, ...)."""
    fig, ax = new_fig(h=h, w=w, left=left, pad=pad)
    ax.remove()
    return fig


def grid(fig, nrows, ncols, **kw):
    """GridSpec filling the plot area of a blank_fig / new_fig (respects the headline and footnote margins)."""
    sp = fig.subplotpars
    return fig.add_gridspec(nrows, ncols, top=sp.top, bottom=sp.bottom, left=sp.left, right=sp.right, **kw)


def month_axis(ax, every=3, fmt="%b %y"):
    """Readable month ticks on a date axis."""
    import matplotlib.dates as mdates
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=every))
    ax.xaxis.set_major_formatter(mdates.DateFormatter(fmt))
    return ax
