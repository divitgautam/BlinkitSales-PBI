# Live model checks (Power BI Desktop, read-only DAX via pbi-cli)

Run 2026-11-27 against the open, refreshed BlinkitSales-PBI model. Tolerance 0.01% (rounded display values compared at their shown precision).

| Check | Expected | Live | Result |
|---|---|---|---|
| Rows fact_orders / fact_marketing / fact_inventory | 5000 / 5400 / 5571 | 5000 / 5400 / 5571 | pass |
| Rows dim_product / dim_customer | 268 / 2500 | 268 / 2500 | pass |
| Date table range | 1 Mar 2023 to 30 Nov 2024 (641 days) | same, 641 rows | pass |
| Revenue | 11,009,308.50 | 11,009,308.50 | pass |
| Orders | 5,000 | 5000 | pass |
| AOV | 2,201.86 | 2,201.8617 | pass |
| Customers Ordering | 2,172 | 2172 | pass |
| Repeat Rate | 68.7% | 68.69% (1,492 repeat customers) | pass |
| On-Time % | 69.4% | 69.4% | pass |
| Avg Minutes Late (all / late only) | 4.44 / 14.49 | 4.443 / 14.488 | pass |
| Avg Rating | 3.34 | 3.3444 | pass |
| Poor Experience Rate | 45.8% | 45.78% | pass |
| Revenue at Risk | 5,042,193.50 | 5,042,193.50 | pass |
| Line Value | 4,972,415 (49.72 L) | 4,972,415.43 | pass |
| Marketing Spend / Revenue | 1.63 Cr / 3.22 Cr | 16,319,838.24 / 32,193,407.37 | pass |
| ROAS | 1.97 | 1.9727 | pass |
| CTR | n/a in reconciliation | 10.086% (29.49 M impressions, 2.97 M clicks) | info |
| Conversion Rate | n/a in reconciliation | 10.02% | info |
| Damage Rate | 3.85% | 3.8535% (1,109 / 28,779) | pass |
| Category line value, all 11 categories | see reconciliation.md | all 11 equal to the rupee; shares 12.9% ... 6.2% | pass |
| ROAS App / Email / SMS / Social | 1.92 / 2.05 / 1.99 / 1.94 | 1.9165 / 2.0486 / 1.9854 / 1.9440 | pass |
| Spend and revenue by channel | per reconciliation.md | App 4,213,379 / 8,075,010; Email 3,997,488 / 8,189,332; SMS 3,998,608 / 7,938,649; Social 4,110,364 / 7,990,416 | pass |
| Revenue Apr 2023 / Oct 2023 / Feb 2024 | 554,345 / 578,370 / 545,090 | 554,344.77 / 578,369.83 / 545,090.11 | pass |
| Revenue Apr / Aug / Oct 2024 | 538,755 / 546,195 / 537,703 | 538,754.75 / 546,194.57 / 537,702.94 | pass |
| YoY Apr / Aug / Oct 2024 | -2.8% / -12.4% / -7.0% | -2.81% / -12.39% / -7.03% | pass |
| YoY and PY blank outside Apr-Oct 2024 (Feb 2024, Oct 2023) | BLANK | BLANK | pass |
| Partial months Mar 2023 and Nov 2024: Revenue (Full Months) | BLANK | BLANK (Revenue 272,879 and 68,158) | pass |
| All measures in _Measures evaluated once | no error | all but Title Sales evaluate; Title Sales errors (see below) | 1 fail |
| Title Sales | text | error: Failed to resolve name 'SYNTAXERROR' | FAIL |
| Title Overview under Dairy & Breakfast filter | changes | 12.44 L revenue from 566 orders; 28% late; 47% at risk | pass |
| Title Delivery under Dairy & Breakfast filter | changes | 72% on time, 14.4 minutes over | pass |
| Title Experience under Dairy & Breakfast filter | changes | 3.37 vs 3.21: "late orders rate higher" | pass |
| Title Marketing under Email filter | changes | Each 1 of spend returns 2.05; Email leads at 2.05x, Email trails at 2.05x | pass (wording issue) |
| Title Marketing under Dairy filter | unchanged (no relationship from product to marketing) | unchanged | pass |

Notes
- Measures that show BLANK at the all-data level by design: Revenue/Orders/AOV/Marketing Spend PY and YoY % (Comparable Period = 0 because the range includes partial months).
- pbi-cli fails on Currency (Decimal) results in ROW(); those measures were read with CONVERT(..., DOUBLE).

## Defect: Title Sales does not parse

`_Measures.tmdl` line 466 / `_build/measures_spec.py`: `VAR top = TOPN ( 1, cats, [Line Value], DESC )`. `top` is a reserved word in DAX, so the measure is stored as invalid (SYNTAXERROR). Test query with `top` renamed to `t1` and `total` to `tot` returns: "Dairy & Breakfast leads with 12.9% of line value; the top 3 categories hold 36%". Fix: rename the variable (`t1`, and use it in `topName` and `topShare`).

## Title texts (live, all data)

| Title | Text | Chars |
|---|---|---|
| Title Overview | 1.10 Cr revenue from 5,000 orders; 31% arrive late and 46% of revenue is at risk | 81 |
| Title Sales | error | n/a |
| Title Monthly Trend | Monthly revenue stays between 5.05 L and 6.23 L (full months only) | 68 |
| Title Delivery | 69% of orders arrive within 5 minutes of the promise; the late ones run 14.5 minutes over | 89 |
| Title Experience | Late orders rate 3.37 vs 3.33 for on-time orders: delay does not move the rating | 80 |
| Title Revenue at Risk | 50.42 L (46% of revenue) sits in orders that were late or rated 1-2 stars | 74 |
| Title Marketing | Each 1 of spend returns 1.97 attributed revenue; Email leads at 2.05x, App trails at 1.92x | 92 |
| Title Insights | 1.10 Cr revenue, 31% of orders late, ROAS 1.97x: five findings and the data caveats | 84 |
| Title Forecast | Full months average 5.61 L of revenue, of which 2.58 L a month is at risk | 75 |
| Title Category Detail | All categories: 100.0% of line value, 69% delivered on time, rating 3.34 | 72 |
| Title Campaign Detail | All campaigns: ROAS 1.97x on 1.63 Cr spend | 43 |

(Rupee signs omitted from this table; the live text carries them.) Titles over 70 characters: Overview, Delivery, Experience, Revenue at Risk, Marketing, Insights, Forecast, Category Detail. Title Marketing reads "Email trails at 2.05x" when one channel is selected; Title Category Detail reads "100.0% of line value" with no category selected.
