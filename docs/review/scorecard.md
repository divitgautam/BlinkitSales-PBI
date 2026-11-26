# Scorecard: BlinkitSales-PBI · 2026-11-27 · reviewer: Claude (expert rubric v1)

Evidence: PDF export docs/BlinkitSales-PBI.pdf (7 pages, PNGs in docs/dashboard/), reconciliation.md, live_checks.md,
bpa_check.py (27/27 pass, 161 measures, 6 relationships). User-confirmed: slicer sync p1-4, category drill-through,
tooltips, phone layout, heat map/sentiment colours. Not confirmed: campaign drill-through.

| # | Criterion | Score | Evidence | Fix to reach 1.0 |
|---|---|---|---|---|
| 1 | Purpose and message | 0.75 | Action titles with numbers on all 7 pages, DAX-driven (Title Sales now renders on p2). p4 visual title says "100% of revenue at risk" (wrong message). | Fix p4 title (fix 1). |
| 2 | Data trust | 0.75 | Cards p1-7 match reconciliation (1.10 Cr, 5,000, 2,201.86, 69.4%, 30.6%, 14.5, 3.34, 45.8%, 68.7%, ROAS 1.97, 29.49 M, 2.97 M, 6.39 L...). Footer source/refresh on every page. Exception: p4 "100%". | Fix 1. |
| 3 | KPI design | 0.5 | Change lines only on p1/p2 revenue; p3-p7 cards have no target/trend/delta. p5 ROAS card says "0.00x vs all campaigns" (meaningless). Caption line collides with the big number on every card. | Fix 3, 4. |
| 4 | Chart choice and honesty | 0.75 | Bars from zero, sorted, no dual axis, forecast band shown. Issues: p7 KPI "Exposure removed 4.95 L" adds late (2.64) and low-rating (2.31) exposures that overlap (14% both) while the same page says they are not additive; p5 matrix column "All" is an audience value and reads as a total (App 1.82x vs bar 1.92x); lines on p1/p5/p7 use a near-flat band with half the plot empty. | Fix 2, 6. |
| 5 | Layout and hierarchy | 0.5 | p1 is clipped in the export: 4th card cut at right, right-hand panel and bottom row cut off, no footer or nav visible. p2 heat map has a scrollbar and cuts months after Jun 24; Top 8 products and campaign lists scroll (6 of 8, 8 of 9 visible). Nav buttons show truncated labels ("1...", "7..."), inconsistent with "2 Sales". Large empty areas on p6 left panel, p3 text panel. | Fix 1b, 5. |
| 6 | Colour and accessibility | 0.75 | Green brand, RdBu variance and YlGn matrices, status red/amber/green with extra cues; amber label on p3 hour bars carries no status meaning; small grey caption text on light cards is borderline on contrast. Alt text not verified in PDF. | Verify alt text and contrast. |
| 7 | Declutter, text, format | 0.75 | Units in subtitles, direct labels, one type scale. Heat map values "0.16" lack unit in cells; p5 ROAS card label truncated ("ROAS (revenue per 1..."), p7 "Exposure removed by levers ..." and "Attributed, not order re..." truncated. | Fix 4. |
| 8 | Interaction, navigation, devices | 0.75 | Synced slicers, category drill-through, tooltips, phone layout confirmed. Campaign drill-through not confirmed; no clear-filters button seen. | Confirm campaign drill-through, add reset bookmark. |
| 9 | Insight and action | 1.0 | p6 ranks five findings with numbers, caveats and "Do next"; p7 sizes levers with confidence, backtest MAPE 2.8%, 80% band. | None. |
| 10 | Model and engineering | 1.0 | BPA 27/27, star schema, generators, DIVIDE, descriptions. Live check outstanding item (Title Sales) is fixed in TMDL and renders. Re-run live_checks for Title Marketing wording. | None. |
| | Gates applied | max 5 | p4: "₹50.42 L (100% of revenue)" contradicts reconciliation (46%); p1 clipped in export (cap 7); p7 non-additive KPI (cap 6, if kept). | |
| | **Raw total** | 7.5 | | |
| | **Final (after gate)** | **5.0 / 10** | Reaches about 9 once fixes 1-4 are done. | |

## Ranked fixes
1. **p4 bottom-right visual title** ("₹50.42 L (100% of revenue) at risk"): the % is evaluated with good-experience class filtered out, so denominator is only poor orders. Use a measure with ALL(revenue) denominator (46%) or drop the %. Owner: Title Revenue at Risk in `_build/measures_spec.py`, and its binding on page 4 in `_build/build_report.py`. 1b: p1 clipped export: check page 1 width/height and visual positions in the page-1 function of `build_report.py` (cards and right panel exceed 1280x720; cards are 4 not 5 wide).
2. **p7 KPI "Exposure removed by levers ₹4.95 L"**: overlapping late and low-rating exposures summed. Replace with the late-deliveries lever alone or the exposure of (late OR low) after both cuts; measure in `measures_spec.py` (lever measures), card in the p7 section of `build_report.py`.
3. **KPI cards p3-p7**: caption overlaps the big value; increase card height or move caption offset in the card helper in `_build/pbir_kit.py`/`build_report.py`; add vs-PY or trend lines to p3-p5 cards (late share, rating, ROAS vs last month).
4. **p5 ROAS card** "0.00x vs all campaigns": remove or replace with a month delta; shorten truncated card labels (p5 ROAS, Attributed revenue, p7 Exposure).
5. **Scrolling visuals**: p2 category-month matrix (cut at Jun 24; limit to last 12 months or widen), Top 8 products (6 visible), p5 campaign list (8 of 9); nav button labels truncated, make uniform ("1 Overview" ... "7 Forecast") and widen.
6. **p5 matrix**: rename column "All" to "Audience: All" or add a total column that matches the bar chart; add unit (x) already ok; p2 heat map cells show "0.16" but title says lakh, add "L" via format.
7. Confirm campaign drill-through, add clear-filters bookmark, verify alt text and caption contrast (grey on light card).
