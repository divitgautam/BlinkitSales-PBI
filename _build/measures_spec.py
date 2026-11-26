"""Measures for BlinkitSales-PBI. Definitions mirror docs/reconciliation.md.
MEASURES = [(name, DAX, formatString, displayFolder, description)]"""
RUPEE = "₹"
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
add("Revenue at Risk %", "DIVIDE ( [Revenue at Risk], [Revenue] )", PCT, E, "Revenue at Risk / Revenue.")
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
for nm, cur, py in (("Revenue", "[Revenue]", "[Revenue PY]"), ("Orders", "[Orders]", "[Orders PY]"), ("AOV", "[AOV]", "[AOV PY]")):
    add(f"Δ {nm}",
        f'VAR p = {py} VAR d = DIVIDE ( {cur} - p, p ) RETURN IF ( ISBLANK ( p ), "No like-for-like year (partial months)", '
        f'IF ( d >= 0, "{UP}", "{DOWN}" ) & FORMAT ( ABS ( d ), "0.0%", "en-US" ) & " vs last year" )', None, P,
        f"Card change line for {nm}: arrow and change vs last year; says so when the comparison is not like-for-like.")
    add(f"Δ {nm} Color", f'VAR p = {py} RETURN IF ( ISBLANK ( p ), "{NEUTRAL}", IF ( {cur} >= p, "{GOOD}", "{BAD}" ) )', None, P,
        f"Colour of the {nm} change line: green up, red down, grey when not comparable.")
add("Δ Revenue at Risk", f'{fm("[Revenue at Risk %]", "0%")} & " of revenue"', None, P, "Card line: Revenue at Risk as a share of revenue.")
add("Δ On-Time %", f'"Late: " & {fm("[Late %]", "0.0%")} & ", " & {fm("[Avg Minutes Late (Late Orders)]", "0.0")} & " min over"', None, P,
    "Card line: late share and how late.")
add("Δ Neutral Color", f'"{NEUTRAL}"', None, P, "Grey for card lines that carry context, not a change.")
add("Selected Category", 'SELECTEDVALUE ( dim_product[Category], "All categories" )', None, P, "Category in the current filter context (drill-through title).")
add("Selected Campaign", f'SELECTEDVALUE ( {MK}[Campaign Name], "All campaigns" )', None, P, "Campaign in the current filter context (drill-through title).")
add("Footer Text",
    f'"Source: Blinkit sales dataset (Kaggle, synthetic)  ·  Orders " & FORMAT ( CALCULATE ( MIN ( {O}[Order Date] ), REMOVEFILTERS () ), "d mmm yyyy", "en-US" ) & " to " '
    f'& FORMAT ( CALCULATE ( MAX ( {O}[Order Date] ), REMOVEFILTERS () ), "d mmm yyyy", "en-US" ) & "  ·  Currency assumed INR  ·  Mar 2023 and Nov 2024 are partial months, left out of trends and YoY"',
    None, P, "Footer: source, data period, currency assumption and the partial-month caveat.")
# 8 Titles: action titles that follow the slicers
TT = "8 Titles"
add("Title Overview",
    f"VAR r = [Revenue] RETURN {inr('r')} & \" revenue from \" & {fm('[Orders]', '#,##0')} & \" orders; \" & {fm('[Late %]', '0%')} & \" arrive late and \" & {fm('[Revenue at Risk %]', '0%')} & \" of revenue is at risk\"",
    None, TT, "Page 1 headline: revenue, orders, late share and revenue at risk.")
add("Title Sales",
    "VAR cats = ALLSELECTED ( dim_product[Category] ) VAR tot = CALCULATE ( [Line Value], ALLSELECTED ( dim_product[Category] ) ) "
    "VAR t1 = TOPN ( 1, cats, [Line Value], DESC ) VAR topName = MAXX ( t1, dim_product[Category] ) VAR topShare = DIVIDE ( MAXX ( t1, [Line Value] ), tot ) "
    "VAR top3 = DIVIDE ( SUMX ( TOPN ( 3, cats, [Line Value], DESC ), [Line Value] ), tot ) "
    f"RETURN topName & \" leads with \" & {fm('topShare', '0.0%')} & \" of line value; the top 3 categories hold \" & {fm('top3', '0%')}",
    None, TT, "Page 2 headline: leading category by line value, its share and the top-3 share.")
add("Title Monthly Trend",
    "VAR m = CALCULATETABLE ( VALUES ( 'Date'[Month Start] ), 'Date'[Is Full Month] = TRUE () ) VAR lo = MINX ( m, [Revenue] ) VAR hi = MAXX ( m, [Revenue] ) "
    f"RETURN \"Monthly revenue stays between \" & {inr('lo')} & \" and \" & {inr('hi')} & \" (full months only)\"",
    None, TT, "Monthly revenue chart title: low and high month among full months.")
add("Title Delivery",
    f"{fm('[On-Time %]', '0%')} & \" of orders arrive within 5 minutes of the promise; the late ones run \" & {fm('[Avg Minutes Late (Late Orders)]', '0.0')} & \" minutes over\"",
    None, TT, "Page 3 headline: on-time share and how late the misses are.")
add("Title Experience",
    "VAR gap = [Rating Gap Late vs On-Time] "
    f"RETURN \"Late orders rate \" & {fm('[Avg Rating Late]', '0.00')} & \" vs \" & {fm('[Avg Rating On-Time]', '0.00')} & \" for on-time orders: \" & "
    "IF ( ISBLANK ( gap ), \"no comparison in this selection\", IF ( ABS ( gap ) < 0.1, \"delay does not move the rating\", IF ( gap < 0, \"delay lowers the rating\", \"late orders rate higher\" ) ) )",
    None, TT, "Page 4 headline: mean rating of late vs on-time orders and what the gap says.")
add("Title Revenue at Risk",
    f"VAR v = [Revenue at Risk] RETURN {inr('v')} & \" (\" & {fm('[Revenue at Risk %]', '0%')} & \" of revenue) sits in orders that were late or rated 1-2 stars\"",
    None, TT, "Revenue at Risk headline.")
add("Title Marketing",
    f"VAR ch = ALLSELECTED ( {MK}[Channel] ) VAR hi = MAXX ( ch, [ROAS] ) VAR lo = MINX ( ch, [ROAS] ) "
    f"VAR hiName = MAXX ( TOPN ( 1, ch, [ROAS], DESC ), {MK}[Channel] ) VAR loName = MAXX ( TOPN ( 1, ch, [ROAS], ASC ), {MK}[Channel] ) "
    f"RETURN \"Each {RUPEE}1 of spend returns {RUPEE}\" & {fm('[ROAS]', '0.00')} & \" attributed revenue; \" & hiName & \" leads at \" & {fm('hi', '0.00')} & \"x, \" & loName & \" trails at \" & {fm('lo', '0.00')} & \"x\"",
    None, TT, "Page 5 headline: portfolio ROAS and the best and worst channel.")
add("Title Insights",
    f"VAR r = [Revenue] RETURN {inr('r')} & \" revenue, \" & {fm('[Late %]', '0%')} & \" of orders late, ROAS \" & {fm('[ROAS]', '0.00')} & \"x: five findings and the data caveats\"",
    None, TT, "Page 6 headline: revenue, late share and ROAS.")
add("Title Forecast",
    f"VAR a = [Avg Monthly Revenue] VAR b = [Avg Monthly Revenue at Risk] RETURN \"Full months average \" & {inr('a')} & \" of revenue, of which \" & {inr('b')} & \" a month is at risk\"",
    None, TT, "Page 7 headline: average monthly revenue and revenue at risk (full months).")
add("Title Category Detail",
    "[Selected Category] & \": \" & " + fm('[Category Share]', '0.0%') + " & \" of line value, \" & " + fm('[On-Time %]', '0%') + " & \" delivered on time, rating \" & " + fm('[Avg Rating]', '0.00'),
    None, TT, "Category drill-through headline.")
add("Title Campaign Detail",
    f"VAR s = [Marketing Spend] RETURN [Selected Campaign] & \": ROAS \" & {fm('[ROAS]', '0.00')} & \"x on \" & {inr('s')} & \" spend\"",
    None, TT, "Campaign drill-through headline.")
