"""'Quick Commerce' theme for BlinkitSales-PBI: Blinkit-inspired palette (brand yellow and green, no logos), dark-green header band.
Imported by build_report.py before the shared kit names are used.

Colour rules: brand GREEN is the primary category colour (contrast 4.9:1 on white); brand YELLOW is decoration only (accent bars, header
stripe) because it fails 3:1 on white; GOLD (3.3:1) is the data-ink version of yellow; CORAL marks bad; GREY is context.
Magnitudes use ColorBrewer YlGn (sequential); variances use ColorBrewer RdBu (colourblind safe) with light ends so dark text stays readable."""

NAVY = "#0A3D1F"         # header band (deep brand green)
NAVY_2 = "#0F5A2B"
GREEN = "#0C831F"        # Blinkit green: primary series
YELLOW = "#F8CB46"       # Blinkit yellow: decoration, accent bars
GOLD = "#B98300"         # data-ink yellow (3.3:1 on white)
CORAL = "#C0392B"        # bad / late
GOOD = "#1E7F4B"
GREY = "#A9B4BC"         # context
SLATE = "#5E6B73"
INK, MUTED, BG, LINE, WHITE = "#13241A", "#58665F", "#F5F7F1", "#DCE3D8", "#FFFFFF"
SUBTITLE, ROW_ALT, BAND = "#CFE8D4", "#F1F6EC", "#8C9AA3"
FONT = "'Segoe UI', sans-serif"
FONT_BOLD = "'Segoe UI Semibold', 'Segoe UI', sans-serif"
# ColorBrewer YlGn 5-class (sequential, magnitudes) and RdBu light ends (diverging, variance from the portfolio)
SEQ_MIN, SEQ_MAX = "#FFFFCC", "#31A354"
DIV_LOW, DIV_MID, DIV_HIGH = "#92C5DE", "#F7F7F7", "#F4A582"


def header_svg(width=1280, height=72):
    """Deep-green band with faint dotted delivery routes and a stopwatch emblem (generic, not the Blinkit logo)."""
    arcs = [((140, 64), (400, -4), (700, 54)), ((380, 70), (660, 6), (940, 58)), ((640, 66), (920, 0), (1200, 44)), ((40, 58), (250, 22), (470, 68))]
    paths = "".join(f'<path d="M{a[0]} {a[1]} Q{b[0]} {b[1]} {c[0]} {c[1]}" fill="none" stroke="{YELLOW}" stroke-opacity=".30" '
                    f'stroke-width="1.4" stroke-dasharray="2 6" stroke-linecap="round"/>' for a, b, c in arcs)
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="2.4" fill="{YELLOW}" fill-opacity=".6"/>'
                   for (x, y), _, (x2, y2) in arcs for x, y in ((x, y), (x2, y2)) if 0 < y < height)
    emblem = (f'<circle cx="34" cy="36" r="21" fill="{YELLOW}"/><circle cx="34" cy="36" r="15" fill="none" stroke="{NAVY}" stroke-width="2.5"/>'
              f'<path d="M34 36 L34 26 M34 36 L41 40" stroke="{NAVY}" stroke-width="2.8" stroke-linecap="round" fill="none"/>'
              f'<rect x="31" y="11" width="6" height="4" rx="1" fill="{NAVY}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{NAVY}"/>'
            f'<stop offset="1" stop-color="{NAVY_2}"/></linearGradient></defs>'
            f'<rect width="{width}" height="{height}" fill="url(#g)"/>{paths}{dots}'
            f'<rect y="{height - 3}" width="{width}" height="3" fill="{YELLOW}"/>{emblem}</svg>')


def apply(kit):
    """Point the shared PBIR kit at this theme (kit TEAL = primary series, AMBER = decorative accent bars)."""
    kit.set_theme(NAVY=NAVY, TEAL=GREEN, AMBER=YELLOW, CORAL=CORAL, SLATE=SLATE, GREEN=GOOD,
                  INK=INK, MUTED=MUTED, BG=BG, LINE=LINE, WHITE=WHITE, FONT=FONT, FONT_BOLD=FONT_BOLD,
                  SUBTITLE=SUBTITLE, ROW_ALT=ROW_ALT, EXTRA_COLORS=[GOLD, GREY],
                  THEME_NAME="QuickCommerce", THEME_FILE="QuickCommerce.json",
                  HEADER_IMAGE="header_quick.svg", HEADER_TEXT_X=64, IMAGES={"header_quick.svg": header_svg()})
