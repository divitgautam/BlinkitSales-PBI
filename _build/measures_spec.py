"""Measures for BlinkitSales-PBI. Definitions mirror docs/reconciliation.md; forecast numbers come from data/clean/report_facts.json.
MEASURES = [(name, DAX, formatString, displayFolder, description)]"""
import json
from pathlib import Path

RUPEE = "₹"
_f = Path(__file__).resolve().parents[1] / "data" / "clean" / "report_facts.json"
FACTS = json.loads(_f.read_text(encoding="utf-8")) if _f.exists() else {}
R0, R2, PCT, PCT2, INT, DEC2 = f"{RUPEE}#,##0", f"{RUPEE}#,##0.00", "0.0%", "0.00%", "#,##0", "0.00"
O, MK, IV = "fact_orders", "fact_marketing", "fact_inventory"
MEASURES = []


def add(name, expr, fmt, folder, desc):
    MEASURES.append((name, expr, fmt, folder, desc))


def inr(v):
    """DAX text for an amount held in VAR v: crore, lakh or plain rupees, 2 decimals (as in docs/reconciliation.md)."""
    return (f'IF ( {v} >= 10000000, "{RUPEE}" & FORMAT ( DIVIDE ( {v}, 10000000 ), "0.00", "en-US" ) & " Cr", '
            f'IF ( {v} >= 100000, "{RUPEE}" & FORMAT ( DIVIDE ( {v}, 100000 ), "0.00", "en-US" ) & " L", "{RUPEE}" & FORMAT ( {v}, "#,##0", "en-US" ) ) )')


def fm(x, p):
    return f'FORMAT ( {x}, "{p}", "en-US" )'


# 1 Sales
S = "1 Sales"
add("Revenue", f"SUM ( {O}[Order Total] )", R0, S, "Revenue = sum of order totals (order header), in assumed INR. The revenue measure for every card and title.")
add("Orders", f"COUNTROWS ( {O} )", INT, S, "Number of orders (one row per order).")
add("AOV", "DIVIDE ( [Revenue], [Orders] )", R2, S, "Average order value = Revenue / Orders.")
add("Customers Ordering", f"DISTINCTCOUNT ( {O}[Customer Id] )", INT, S,
    "Distinct customers with at least one order in the selection (the customer file has 2,500, of whom 2,172 order).")
add("Repeat Customers", f"COUNTROWS ( FILTER ( VALUES ( {O}[Customer Id] ), CALCULATE ( COUNTROWS ( {O} ) ) >= 2 ) )", INT, S,
    "Customers with two or more orders in the selection.")
add("Repeat Rate", "DIVIDE ( [Repeat Customers], [Customers Ordering] )", PCT, S, "Repeat customers / customers ordering.")
add("Units Sold", f"SUM ( {O}[Quantity] )", INT, S, "Units on the order item lines.")
add("Revenue per Customer", "DIVIDE ( [Revenue], [Customers Ordering] )", R2, S, "Revenue / customers ordering.")
add("Line Value", f"SUM ( {O}[Line Amount] )", R0, S,
    "Quantity x unit price on the item lines, in assumed INR. Use ONLY for category and product mix: it does not reconcile to Revenue (about 45% of it in the source).")
add("Category Share", "DIVIDE ( [Line Value], CALCULATE ( [Line Value], ALLSELECTED ( dim_product[Category] ) ) )", PCT, S,
    "Category share of line value within the current selection (use with Category on an axis).")
add("Category Rank", "IF ( NOT ISBLANK ( [Line Value] ), RANKX ( ALLSELECTED ( dim_product[Category] ), [Line Value], , DESC, DENSE ) )", "0", S,
    "Dense rank of a category by line value within the selection.")
add("Avg Margin %", "DIVIDE ( AVERAGE ( dim_product[Margin Percentage] ), 100 )", PCT, S, "Average stored margin of the products in the selection (simple average across products).")
# 2 Delivery
D = "2 Delivery"
add("On-Time Orders", f'CALCULATE ( [Orders], {O}[Delivery Status] = "On Time" )', INT, D, "Orders delivered On Time (includes up to 5 minutes late).")
add("On-Time %", "DIVIDE ( [On-Time Orders], [Orders] )", PCT, D, "On-time orders / orders. Late % = 1 - On-Time %.")
add("Late Orders", f"CALCULATE ( [Orders], {O}[Is Late] = TRUE () )", INT, D, "Orders not delivered On Time (Slightly or Significantly Delayed).")
add("Late %", "DIVIDE ( [Late Orders], [Orders] )", PCT, D, "Late orders / orders.")
add("Slightly Delayed %", f'DIVIDE ( CALCULATE ( [Orders], {O}[Delivery Status] = "Slightly Delayed" ), [Orders] )', PCT, D, "Share of orders with status Slightly Delayed.")
add("Significantly Delayed %", f'DIVIDE ( CALCULATE ( [Orders], {O}[Delivery Status] = "Significantly Delayed" ), [Orders] )', PCT, D,
    "Share of orders with status Significantly Delayed.")
add("Avg Minutes Late", f"AVERAGE ( {O}[Minutes Late] )", DEC2, D, "Mean of minutes late; early deliveries count as negative minutes.")
add("Avg Minutes Late (Late Orders)", f"CALCULATE ( AVERAGE ( {O}[Minutes Late] ), {O}[Is Late] = TRUE () )", DEC2, D, "Mean minutes late among late orders only.")
add("Avg Distance Km", f"AVERAGE ( {O}[Distance Km] )", DEC2, D, "Mean delivery distance in kilometres.")
# 3 Experience
E = "3 Experience"
add("Avg Rating", f"AVERAGE ( {O}[Rating] )", DEC2, E, "Mean customer rating, 1-5 stars.")
add("Avg Rating On-Time", f'CALCULATE ( [Avg Rating], {O}[Delivery Status] = "On Time" )', DEC2, E, "Mean rating of on-time orders.")
add("Avg Rating Late", f"CALCULATE ( [Avg Rating], {O}[Is Late] = TRUE () )", DEC2, E, "Mean rating of late orders.")
add("Rating Gap Late vs On-Time", "[Avg Rating Late] - [Avg Rating On-Time]", "+0.00;-0.00;0.00", E,
    "Late minus on-time mean rating; near zero means delay does not move the rating in this data.")
add("Poor Experience Orders", f"CALCULATE ( [Orders], {O}[Poor Experience] = TRUE () )", INT, E, "Orders that were late or rated 1-2 stars.")
add("Poor Experience Rate", "DIVIDE ( [Poor Experience Orders], [Orders] )", PCT, E, "Poor-experience orders / orders.")
add("Revenue at Risk", f"CALCULATE ( [Revenue], {O}[Poor Experience] = TRUE () )", R0, E,
    "HEADLINE KPI. Sum of order totals of poor-experience orders (late or rated 1-2 stars) = Orders x Poor Experience Rate x AOV of those orders.")
add("Revenue at Risk %", f"DIVIDE ( [Revenue at Risk], CALCULATE ( [Revenue], REMOVEFILTERS ( {O}[Experience Class] ) ) )", PCT, E,
    "Revenue at Risk / total revenue. The Experience Class filter is removed from the denominator, so a visual that hides good-experience orders still shows the share of ALL revenue.")
add("Low Rating Orders", f"CALCULATE ( [Orders], {O}[Rating] <= 2 )", INT, E, "Orders rated 1 or 2 stars.")
add("Low Rating %", "DIVIDE ( [Low Rating Orders], [Orders] )", PCT, E, "Low-rating orders / orders.")
add("Negative Sentiment %", f'DIVIDE ( CALCULATE ( [Orders], {O}[Sentiment] = "Negative" ), [Orders] )', PCT, E, "Share of orders with negative feedback sentiment.")
# 4 Marketing
K = "4 Marketing"
add("Marketing Spend", f"SUM ( {MK}[Spend] )", R0, K, "Campaign spend in assumed INR.")
add("Marketing Revenue", f"SUM ( {MK}[Attributed Revenue] )", R0, K,
    "Revenue attributed to campaigns by the source. Not order revenue (it is 2.9x total order revenue) and cannot be reconciled to orders.")
add("ROAS", "DIVIDE ( [Marketing Revenue], [Marketing Spend] )", "0.00\\x", K,
    "Return on ad spend = attributed revenue / spend, recomputed (the stored roas column did not match).")
add("ROAS vs Portfolio", f"IF ( NOT ISBLANK ( [ROAS] ), [ROAS] - CALCULATE ( [ROAS], REMOVEFILTERS ( {MK} ) ) )", "+0.00;-0.00;0.00", K,
    "ROAS minus the all-campaign ROAS: variance for diverging colour scales.")
add("Total Impressions", f"SUM ( {MK}[Impressions] )", INT, K, "Impressions served.")
add("Total Clicks", f"SUM ( {MK}[Clicks] )", INT, K, "Clicks.")
add("Total Conversions", f"SUM ( {MK}[Conversions] )", INT, K, "Conversions.")
add("CTR", "DIVIDE ( [Total Clicks], [Total Impressions] )", PCT2, K, "Click-through rate = clicks / impressions.")
add("Conversion Rate", "DIVIDE ( [Total Conversions], [Total Clicks] )", PCT, K, "Conversion rate = conversions / clicks.")
add("Cost per Conversion", "DIVIDE ( [Marketing Spend], [Total Conversions] )", R2, K, "Spend / conversions.")
add("Cost per Click", "DIVIDE ( [Marketing Spend], [Total Clicks] )", R2, K, "Spend / clicks.")
# 5 Inventory
V = "5 Inventory"
add("Stock Received", f"SUM ( {IV}[Units Received] )", INT, V, "Units received (monthly inventory file, summed to product x month).")
add("Damaged Stock", f"SUM ( {IV}[Units Damaged] )", INT, V, "Units damaged.")
add("Damage Rate", "DIVIDE ( [Damaged Stock], [Stock Received] )", PCT2, V, "Damaged units / units received.")
# 6 Trends (YoY only where both periods are full months)
Y = "6 Trends"
add("Partial Months in Context", "CALCULATE ( COUNTROWS ( 'Date' ), 'Date'[Is Full Month] = FALSE () )", "0", Y,
    "Number of days in the selection that fall in a partial month (Mar 2023, Nov 2024).")
add("Comparable Period",
    "VAR cur = CALCULATE ( COUNTROWS ( 'Date' ), 'Date'[Is Full Month] = FALSE () ) "
    "VAR py = CALCULATE ( COUNTROWS ( 'Date' ), SAMEPERIODLASTYEAR ( 'Date'[Date] ), 'Date'[Is Full Month] = FALSE () ) "
    "RETURN IF ( cur + py = 0, 1, 0 )", "0", Y,
    "1 when neither the selected period nor the same period last year touches a partial month, else 0. Guards every YoY measure.")
for nm, base, fmt in (("Revenue", "[Revenue]", R0), ("Orders", "[Orders]", INT), ("AOV", "[AOV]", R2), ("Marketing Spend", "[Marketing Spend]", R0)):
    add(f"{nm} PY", f"IF ( [Comparable Period] = 1, CALCULATE ( {base}, SAMEPERIODLASTYEAR ( 'Date'[Date] ) ) )", fmt, Y,
        f"{nm} for the same period last year; blank when either period includes a partial month or last year has no data.")
    add(f"{nm} YoY %", f"DIVIDE ( {base} - [{nm} PY], [{nm} PY] )", PCT, Y, f"{nm} change vs the same period last year; blank unless both periods are full months.")
add("Revenue (Full Months)", "CALCULATE ( [Revenue], 'Date'[Is Full Month] = TRUE () )", R0, Y, "Revenue restricted to full months (blank for Mar 2023 and Nov 2024). Use on monthly trend lines.")
add("Orders (Full Months)", "CALCULATE ( [Orders], 'Date'[Is Full Month] = TRUE () )", INT, Y, "Orders restricted to full months.")
add("Avg Monthly Revenue", "AVERAGEX ( CALCULATETABLE ( VALUES ( 'Date'[Month Start] ), 'Date'[Is Full Month] = TRUE () ), [Revenue] )", R0, Y,
    "Mean revenue per full month in the selection.")
add("Avg Monthly Revenue at Risk", "AVERAGEX ( CALCULATETABLE ( VALUES ( 'Date'[Month Start] ), 'Date'[Is Full Month] = TRUE () ), [Revenue at Risk] )", R0, Y,
    "Mean revenue at risk per full month in the selection.")
# 7 Display: card text, change lines
P = "7 Display"
UP, DOWN = "▲ ", "▼ "
GOOD, BAD, NEUTRAL = "#1E7F4B", "#C0392B", "#5B6B7F"       # WCAG AA on white
add("Card Revenue", f"VAR v = [Revenue] RETURN {inr('v')}", None, P, "Revenue for cards, in crore or lakh.")
add("Card Revenue at Risk", f"VAR v = [Revenue at Risk] RETURN {inr('v')}", None, P, "Revenue at Risk for cards, in crore or lakh.")
add("Card Orders", fm("[Orders]", "#,##0"), None, P, "Orders for cards.")
add("Card AOV", f'"{RUPEE}" & {fm("[AOV]", "#,##0.00")}', None, P, "Average order value for cards.")
add("Card On-Time %", fm("[On-Time %]", "0.0%"), None, P, "On-time rate for cards.")
add("Card Avg Rating", fm("[Avg Rating]", "0.00"), None, P, "Average rating for cards.")
add("Card ROAS", f'{fm("[ROAS]", "0.00")} & "x"', None, P, "ROAS for cards.")
# ---- unit measures for charts (₹ lakh) so axes and data labels carry their unit
LAKH = f"{RUPEE}#,##0.00 \\L"
for nm, base, desc in (("Revenue", "[Revenue]", "Revenue"), ("Line Value", "[Line Value]", "Line value"), ("Revenue at Risk", "[Revenue at Risk]", "Revenue at Risk"),
                       ("Marketing Spend", "[Marketing Spend]", "Marketing spend"), ("Marketing Revenue", "[Marketing Revenue]", "Attributed marketing revenue")):
    add(f"{nm} ₹ L", f"DIVIDE ( {base}, 100000 )", LAKH, P, f"{desc} in ₹ lakh, for chart axes and data labels.")
add("Last Full Month", "CALCULATE ( MAX ( 'Date'[Month Start] ), 'Date'[Is Full Month] = TRUE () )", "mmm yyyy", P,
    "Last full month inside the current date selection (blank when the selection holds no full month). Drives the card change lines.")
add("Category Share of All", "DIVIDE ( [Line Value], CALCULATE ( [Line Value], REMOVEFILTERS ( dim_product ) ) )", PCT, S,
    "Line value share of one category against all categories, ignoring product filters (so it still works on the drill-through page).")
add("Negative Sentiment vs All (pp)",
    f"IF ( NOT ISBLANK ( [Negative Sentiment %] ), ( [Negative Sentiment %] - CALCULATE ( [Negative Sentiment %], REMOVEFILTERS ( {O}[Feedback Category] ) ) ) * 100 )",
    "+0.0;-0.0;0.0", E, "Negative-sentiment share minus the all-orders share, in percentage points (diverging colour in the matrix).")

# ---- cards: text values
card = lambda nm, expr, desc: add(f"Card {nm}", expr, None, P, desc)
card("Late %", fm("[Late %]", "0.0%"), "Late share for cards.")
card("Slightly Delayed %", fm("[Slightly Delayed %]", "0.0%"), "Slightly delayed share for cards.")
card("Significantly Delayed %", fm("[Significantly Delayed %]", "0.0%"), "Significantly delayed share for cards.")
card("Avg Minutes Late", fm("[Avg Minutes Late (Late Orders)]", "0.0") + ' & " min"', "Mean minutes late among late orders, for cards.")
card("Low Rating %", fm("[Low Rating %]", "0.0%"), "Share of orders rated 1-2 stars, for cards.")
card("Poor Experience Rate", fm("[Poor Experience Rate]", "0.0%"), "Poor-experience rate for cards.")
card("Negative Sentiment %", fm("[Negative Sentiment %]", "0.0%"), "Negative sentiment share for cards.")
card("Repeat Rate", fm("[Repeat Rate]", "0.0%"), "Repeat customer rate for cards.")
card("Line Value", f"VAR v = [Line Value] RETURN {inr('v')}", "Line value for cards, in crore or lakh.")
card("Units Sold", fm("[Units Sold]", "#,##0"), "Units sold for cards.")
card("Avg Margin %", fm("[Avg Margin %]", "0.0%"), "Average stored margin for cards.")
card("Revenue per Customer", f'"{RUPEE}" & {fm("[Revenue per Customer]", "#,##0")}', "Revenue per ordering customer for cards.")
card("Marketing Spend", f"VAR v = [Marketing Spend] RETURN {inr('v')}", "Marketing spend for cards.")
card("Marketing Revenue", f"VAR v = [Marketing Revenue] RETURN {inr('v')}", "Attributed marketing revenue for cards.")
card("Impressions", fm("DIVIDE ( [Total Impressions], 1000000 )", "0.00") + ' & " M"', "Impressions in millions, for cards.")
card("Clicks", fm("DIVIDE ( [Total Clicks], 1000000 )", "0.00") + ' & " M"', "Clicks in millions, for cards.")
card("Conversions", fm("[Total Conversions]", "#,##0"), "Conversions for cards.")
# ---- cards: change / context lines (arrows only where there is a like-for-like comparison)
for nm, cur in (("Revenue", "[Revenue]"), ("Orders", "[Orders]"), ("AOV", "[AOV]")):
    head = (f"VAR m = [Last Full Month] VAR pm = EDATE ( m, -12 ) "
            f"VAR ok = NOT ISBLANK ( m ) && CALCULATE ( COUNTROWS ( 'Date' ), ALL ( 'Date' ), 'Date'[Month Start] = pm, 'Date'[Is Full Month] = TRUE () ) > 0 "
            f"VAR c = CALCULATE ( {cur}, ALL ( 'Date' ), 'Date'[Month Start] = m ) VAR p = CALCULATE ( {cur}, ALL ( 'Date' ), 'Date'[Month Start] = pm ) ")
    add(f"Δ {nm}", head + f'RETURN IF ( ISBLANK ( m ), "No full month selected", IF ( NOT ok, FORMAT ( m, "mmm yy", "en-US" ) & ": no prior-year month", '
        f'IF ( c >= p, "{UP}", "{DOWN}" ) & FORMAT ( ABS ( DIVIDE ( c - p, p ) ), "0.0%", "en-US" ) & " " & FORMAT ( m, "mmm yy", "en-US" ) & " vs " & FORMAT ( pm, "mmm yy", "en-US" ) ) )',
        None, P, f"Card change line for {nm}: last full month in the selection vs the same month a year earlier; says so when there is no full prior-year month.")
    add(f"Δ {nm} Color", head + f'RETURN IF ( NOT ok, "{NEUTRAL}", IF ( c >= p, "{GOOD}", "{BAD}" ) )', None, P,
        f"Colour of the {nm} change line: green up, red down, grey when not comparable.")
add("Δ Repeat Rate", f'{fm("[Repeat Customers]", "#,##0")} & " of " & {fm("[Customers Ordering]", "#,##0")} & " customers"', None, P, "Card line: repeat customers over customers ordering.")
# generic like-for-like change lines: last full month in the selection vs the same month a year earlier (arrow, size, both months named)
def yoy(nm, cur, mode, good, unit=""):
    """mode rel: % change; pp: percentage points of a ratio; abs: absolute difference (unit appended). good: up, down or none (colour)."""
    head = (f"VAR m = [Last Full Month] VAR pm = EDATE ( m, -12 ) "
            f"VAR ok = NOT ISBLANK ( m ) && CALCULATE ( COUNTROWS ( 'Date' ), ALL ( 'Date' ), 'Date'[Month Start] = pm, 'Date'[Is Full Month] = TRUE () ) > 0 "
            f"VAR c = CALCULATE ( {cur}, ALL ( 'Date' ), 'Date'[Month Start] = m ) VAR p = CALCULATE ( {cur}, ALL ( 'Date' ), 'Date'[Month Start] = pm ) ")
    size = {"rel": 'FORMAT ( ABS ( DIVIDE ( c - p, p ) ), "0.0%", "en-US" )',
            "pp": 'FORMAT ( ABS ( c - p ) * 100, "0.0", "en-US" ) & " pp"',
            "abs": f'FORMAT ( ABS ( c - p ), "0.00", "en-US" ) & " {unit}"'}[mode]
    add(f"Δ {nm}", head + f'RETURN IF ( ISBLANK ( m ), "No full month selected", IF ( NOT ok || ISBLANK ( c ) || ISBLANK ( p ), "No prior-year month", '
        f'IF ( c >= p, "{UP}", "{DOWN}" ) & {size} & " " & FORMAT ( m, "mmm yy", "en-US" ) & " vs " & FORMAT ( pm, "mmm yy", "en-US" ) ) )',
        None, P, f"Card change line for {nm}: last full month in the selection vs the same month a year earlier; says so when there is no full prior-year month.")
    colour = (f'IF ( NOT ok || ISBLANK ( c ) || ISBLANK ( p ), "{NEUTRAL}", IF ( ( c >= p ) = {"TRUE ()" if good == "up" else "FALSE ()"}, "{GOOD}", "{BAD}" ) )'
              if good in ("up", "down") else f'"{NEUTRAL}"')
    add(f"Δ {nm} Color", head + f"RETURN {colour}", None, P, f"Colour of the {nm} change line: green is good, red is bad, grey when not comparable or when direction has no good side.")


for nm, cur, mode, good, unit in (
        ("On-Time %", "[On-Time %]", "pp", "up", ""), ("Late %", "[Late %]", "pp", "down", ""), ("Slightly Delayed %", "[Slightly Delayed %]", "pp", "down", ""),
        ("Significantly Delayed %", "[Significantly Delayed %]", "pp", "down", ""), ("Avg Minutes Late", "[Avg Minutes Late (Late Orders)]", "abs", "down", "min"),
        ("Avg Rating", "[Avg Rating]", "abs", "up", "pts"), ("Low Rating %", "[Low Rating %]", "pp", "down", ""),
        ("Poor Experience Rate", "[Poor Experience Rate]", "pp", "down", ""), ("Negative Sentiment %", "[Negative Sentiment %]", "pp", "down", ""),
        ("Revenue at Risk", "[Revenue at Risk]", "rel", "down", ""), ("Line Value", "[Line Value]", "rel", "up", ""), ("Units Sold", "[Units Sold]", "rel", "up", ""),
        ("Avg Margin %", "[Avg Margin %]", "pp", "up", ""), ("Revenue per Customer", "[Revenue per Customer]", "rel", "up", ""),
        ("Marketing Spend", "[Marketing Spend]", "rel", "none", ""), ("Marketing Revenue", "[Marketing Revenue]", "rel", "up", ""), ("ROAS", "[ROAS]", "rel", "up", ""),
        ("Impressions", "[Total Impressions]", "rel", "up", ""), ("Clicks", "[Total Clicks]", "rel", "up", ""), ("Conversions", "[Total Conversions]", "rel", "up", ""),
        ("CTR", "[CTR]", "pp", "up", ""), ("Conversion Rate", "[Conversion Rate]", "pp", "up", "")):
    yoy(nm, cur, mode, good, unit)
add("Δ Neutral Color", f'"{NEUTRAL}"', None, P, "Grey for card lines that carry context, not a change.")
add("Selected Category", 'SELECTEDVALUE ( dim_product[Category], "All categories" )', None, P, "Category in the current filter context (drill-through title).")
add("Selected Campaign", f'SELECTEDVALUE ( {MK}[Campaign Name], "All campaigns" )', None, P, "Campaign in the current filter context (drill-through title).")
add("Footer Text",
    f'"Source: Blinkit sales (Kaggle, synthetic) · orders " & FORMAT ( CALCULATE ( MIN ( {O}[Order Date] ), REMOVEFILTERS () ), "d mmm yyyy", "en-US" ) & " to " '
    f'& FORMAT ( CALCULATE ( MAX ( {O}[Order Date] ), REMOVEFILTERS () ), "d mmm yyyy", "en-US" ) & " · INR assumed · refreshed " & FORMAT ( MAX ( \'Refresh Info\'[Refreshed] ), "d mmm yyyy", "en-US" )',
    None, P, "Footer: source, data period, currency assumption and the refresh date.")
# ---- 9 Forecast (disconnected Forecast and Levers tables)
FC = "9 Forecast"
for nm, col_, desc in (("Actual", "Actual", "Actual monthly revenue"), ("Forecast", "Forecast", "Forecast monthly revenue (flat level)"),
                       ("Low", "Low 80", "Low end of the 80% band"), ("High", "High 80", "High end of the 80% band")):
    add(f"Fcst {nm} ₹ L", f"DIVIDE ( SUM ( Forecast[{col_}] ), 100000 )", LAKH, FC, f"{desc}, ₹ lakh; blank outside its months.")
F25 = lambda c: f'CALCULATE ( SUM ( Forecast[{c}] ), Forecast[Year] = 2025, Forecast[Kind] = "Forecast" )'
add("F25 Revenue", F25("Forecast"), R0, FC, "2025 revenue forecast: the sum of the twelve forecast months (flat level model).")
add("F25 Low", F25("Low 80"), R0, FC, "2025 low case: sum of the monthly 80% lower bounds.")
add("F25 High", F25("High 80"), R0, FC, "2025 high case: sum of the monthly 80% upper bounds.")
add("LTM Revenue", "VAR lastA = CALCULATE ( MAX ( Forecast[Month Start] ), Forecast[Kind] = \"Actual\" ) "
    "RETURN CALCULATE ( SUM ( Forecast[Actual] ), Forecast[Month Start] > EDATE ( lastA, -12 ), Forecast[Month Start] <= lastA )", R0, FC,
    "Revenue of the last 12 full months (Nov 2023 to Oct 2024).")
add("F25 vs LTM %", "DIVIDE ( [F25 Revenue] - [LTM Revenue], [LTM Revenue] )", "+0.0%;-0.0%;0.0%", FC, "2025 forecast vs the last 12 full months.")
add("Lever Value", "SUM ( Levers[Annual Value] )", R0, FC, "Annual lever value in ₹ (types are not additive).")
add("Lever Value ₹ L", "DIVIDE ( SUM ( Levers[Annual Value] ), 100000 )", LAKH, FC, "Annual lever value in ₹ lakh, for the lever chart.")
add("Lever Value % of Revenue", "SUM ( Levers[Pct of Revenue] )", PCT, FC, "Lever value as a share of the last 12 full months of revenue.")
add("Lever Exposure Removed", 'CALCULATE ( SUM ( Levers[Annual Value] ), Levers[Lever Type] = "Exposure removed (combined)" )', R0, FC,
    "Revenue at Risk removed when late deliveries and 1-2 star ratings are both cut by 5 points: ONE scenario on late-or-low-rated orders (forecast.py), not the sum of two levers.")
add("Card F25 Revenue", f"VAR v = [F25 Revenue] RETURN {inr('v')}", None, P, "2025 forecast for cards.")
add("Card F25 Range", f"VAR lo = [F25 Low] VAR hi = [F25 High] RETURN {inr('lo')} & \" to \" & {inr('hi')}", None, P, "80% band of the 2025 forecast for cards.")
add("Card F25 vs LTM", f"{fm('ABS ( [F25 vs LTM %] )', '0.0%')} & IF ( [F25 vs LTM %] < 0, \" below\", \" above\" )", None, P, "2025 forecast vs the last 12 months, as text.")
add("Card Backtest", f'"{FACTS.get("backtest_mape", 0):.1f}%"', None, P, "Backtest error (MAPE) of the forecast model, from _build/forecast.py.")
add("Card Lever Exposure", f"VAR v = [Lever Exposure Removed] RETURN {inr('v')}", None, P, "Annual exposure removed by the two experience levers, for cards.")
add("Δ F25 Range", f'"Each month ±{FACTS.get("band80", 0) * 100:.1f}%"', None, P, "Card line: width of the monthly band.")
add("Δ F25 vs LTM", f'"Last 12 months: " & {inr("[LTM Revenue]")}', None, P, "Card line: the last-12-month revenue.")
add("Δ Backtest", f'"{FACTS.get("backtest_best", "model")}"', None, P, "Card line: the winning model of the rolling-origin backtest.")
# 8 Titles: action titles that follow the slicers (every title stays within 70 characters, counting ₹ as one)
TT = "8 Titles"
add("Title Overview",
    f"VAR r = [Revenue] RETURN {inr('r')} & \" revenue, \" & {fm('[Orders]', '#,##0')} & \" orders; \" & {fm('[Late %]', '0%')} & \" late, \" & {fm('[Revenue at Risk %]', '0%')} & \" of revenue at risk\"",
    None, TT, "Page 1 headline: revenue, orders, late share and revenue at risk.")
add("Title Sales",
    "VAR cats = ALLSELECTED ( dim_product[Category] ) VAR tot = CALCULATE ( [Line Value], ALLSELECTED ( dim_product[Category] ) ) "
    "VAR t1 = TOPN ( 1, cats, [Line Value], DESC ) VAR topName = MAXX ( t1, dim_product[Category] ) VAR topShare = DIVIDE ( MAXX ( t1, [Line Value] ), tot ) "
    "VAR top3 = DIVIDE ( SUMX ( TOPN ( 3, cats, [Line Value], DESC ), [Line Value] ), tot ) "
    f"RETURN topName & \" leads at \" & {fm('topShare', '0.0%')} & \" of line value; top 3 hold \" & {fm('top3', '0%')}",
    None, TT, "Page 2 headline: leading category by line value, its share and the top-3 share.")
add("Title Monthly Trend",
    "VAR m = CALCULATETABLE ( VALUES ( 'Date'[Month Start] ), 'Date'[Is Full Month] = TRUE () ) VAR lo = MINX ( m, [Revenue] ) VAR hi = MAXX ( m, [Revenue] ) "
    f"RETURN \"Monthly revenue stays between \" & {inr('lo')} & \" and \" & {inr('hi')} & \" (full months only)\"",
    None, TT, "Monthly revenue chart title: low and high month among full months.")
add("Title Delivery",
    f"{fm('[On-Time %]', '0%')} & \" of orders arrive on time; the late ones run \" & {fm('[Avg Minutes Late (Late Orders)]', '0.0')} & \" minutes over\"",
    None, TT, "Page 3 headline: on-time share and how late the misses are.")
add("Title Experience",
    "VAR a = [Avg Rating Late] VAR b = [Avg Rating On-Time] VAR gap = a - b "
    f"RETURN IF ( ISBLANK ( a ) || ISBLANK ( b ), \"Too few late or on-time orders to compare ratings\", \"Late orders rate \" & {fm('a', '0.00')} & \" vs \" & {fm('b', '0.00')} & \" on time: \" & "
    "IF ( ABS ( gap ) < 0.1, \"delay does not move rating\", IF ( gap < 0, \"delay lowers rating\", \"late orders rate higher\" ) ) )",
    None, TT, "Page 4 headline: mean rating of late vs on-time orders and what the gap says.")
add("Title Revenue at Risk",
    f"VAR v = [Revenue at Risk] RETURN {inr('v')} & \" (\" & {fm('[Revenue at Risk %]', '0%')} & \" of revenue) at risk: late or rated 1-2 stars\"",
    None, TT, "Revenue at Risk headline.")
add("Title Marketing",
    f"VAR ch = ALLSELECTED ( {MK}[Channel] ) VAR n = COUNTROWS ( ch ) VAR hi = MAXX ( ch, [ROAS] ) VAR lo = MINX ( ch, [ROAS] ) VAR s = [Marketing Spend] "
    f"VAR hiName = MAXX ( TOPN ( 1, ch, [ROAS], DESC ), {MK}[Channel] ) VAR loName = MAXX ( TOPN ( 1, ch, [ROAS], ASC ), {MK}[Channel] ) "
    f"RETURN IF ( n = 0 || ISBLANK ( [ROAS] ), \"No marketing data in this selection\", IF ( n = 1, hiName & \": ROAS \" & {fm('[ROAS]', '0.00')} & \"x on \" & {inr('s')} & \" spend\", "
    f"\"ROAS \" & {fm('[ROAS]', '0.00')} & \"x: \" & hiName & \" leads at \" & {fm('hi', '0.00')} & \"x, \" & loName & \" trails at \" & {fm('lo', '0.00')} & \"x\" ) )",
    None, TT, "Page 5 headline: portfolio ROAS and the best and worst channel; one channel selected shows that channel's ROAS and spend.")
add("Title Insights",
    f"VAR r = [Revenue] RETURN {inr('r')} & \" revenue, \" & {fm('[Late %]', '0%')} & \" late, ROAS \" & {fm('[ROAS]', '0.00')} & \"x: five findings, data caveats\"",
    None, TT, "Page 6 headline: revenue, late share and ROAS.")
add("Title Forecast",
    f"VAR v = [F25 Revenue] RETURN \"2025 revenue forecast \" & {inr('v')} & \", \" & {fm('ABS ( [F25 vs LTM %] )', '0%')} & IF ( [F25 vs LTM %] < 0, \" below\", \" above\" ) & \" the last 12 months\"",
    None, TT, "Page 7 headline: 2025 revenue forecast and its change vs the last 12 full months.")
add("Title Category Detail",
    "IF ( DISTINCTCOUNT ( dim_product[Category] ) <> 1, \"Select a category to drill through\", [Selected Category] & \": \" & " + fm('[Category Share of All]', '0.0%') + " & \" of line value, \" & " + fm('[On-Time %]', '0%') + " & \" on time, \" & " + fm('[Avg Rating]', '0.00') + " & \" stars\" )",
    None, TT, "Category drill-through headline (a prompt when no single category is in context).")
add("Title Campaign Detail",
    f"VAR s = [Marketing Spend] RETURN IF ( DISTINCTCOUNT ( {MK}[Campaign Name] ) <> 1, \"Select a campaign to drill through\", [Selected Campaign] & \": ROAS \" & {fm('[ROAS]', '0.00')} & \"x on \" & {inr('s')} & \" spend\" )",
    None, TT, "Campaign drill-through headline (a prompt when no single campaign is in context).")
# ---- extra display measures (heat-map cell value, tooltip cards)
add("Line Value ₹ L Plain", "DIVIDE ( [Line Value], 100000 )", r"0.00 \L", P, "Line value in ₹ lakh with two decimals and no unit text, for the compact category x month heat map.")
card("CTR", fm("[CTR]", "0.00%"), "Click-through rate for cards.")
card("Conversion Rate", fm("[Conversion Rate]", "0.0%"), "Conversion rate for cards.")

add("Δ Lever Exposure", f'{fm("DIVIDE ( [Lever Exposure Removed], [LTM Revenue] )", "0.0%")} & " of 12-month revenue"', None, P, "Card line: combined exposure removed as a share of last-12-month revenue.")
add("Δ F25 Revenue", f'IF ( [F25 vs LTM %] < 0, "{DOWN}", "{UP}" ) & {fm("ABS ( [F25 vs LTM %] )", "0.0%")} & " vs last 12 months"', None, P, "Card line: 2025 forecast vs the last 12 full months.")
add("Δ F25 Revenue Color", f'IF ( [F25 vs LTM %] < 0, "{BAD}", "{GOOD}" )', None, P, "Colour of the forecast change line.")
