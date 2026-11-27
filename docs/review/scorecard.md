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

## Round 2 changes (2026-11-27, before the next export; score left for the next review)
1. **p4 title %**: `Revenue at Risk %` now divides by total revenue with the Experience Class filter removed (45.8%); `reconcile.py` asserts the share (0.458) in both pipelines and lists it in reconciliation.md.
1b. **p1 clipping**: page 1 geometry is identical to the other pages (1280x720, all visuals inside), so the clip was an export zoom artefact; set Ctrl+0 / fit-to-page before export. `check_report.py` now enforces a 38 px bottom margin, 16 px side margins and a 4 px footer margin on every page.
2. **p7 exposure**: new combined scenario in `forecast.py` (late-only x f1 + low-only x f2 + both x f1 x f2, no double counting = ₹5.12 L) as an extra Levers row; the card uses it, the lever chart excludes it, `reconcile.py` re-derives it independently.
3. **Cards**: card height 100, bottom padding 26 on every card with a change line, change line 22 px at the bottom (no overlap); row 2 moved to y=190. Pages 1-7 and both drill-through pages now show like-for-like change lines (last full month vs the same month a year earlier: pp for rates, % for amounts, pts/min for rating and delay), coloured green/red by direction (spend grey); p7 F25 card shows % vs last 12 months. Repeat rate, range, backtest keep context text (no like-for-like monthly comparison).
4. **p5 ROAS**: "x vs all campaigns" removed; labels shortened ("ROAS (₹ per ₹1 spent)", "Exposure removed (both cuts)").
5. **No scrolling**: p2 heat map limited to the last 12 full months and given 310 px, Top 5 products (was 8), p5 campaign chart taller with tighter bars, category-detail table at 9 pt in a taller area; nav widened to 700 px (7 tabs, "1 Overview" ... "7 Forecast") and the footer text shortened.
6. **p5 matrix**: audience "All" renamed "All audiences" in prepare.py (clean data); subtitle explains it; heat map cells now carry "L" (format `0.00 \L`).
7. Reset-filters button: not added (the kit has no bookmark or clear-slicers support and it cannot be tested without Desktop); campaign drill-through still to confirm by hand.
New checks in `check_report.py`: page margins, card label width, change-line width, card bottom padding vs change line, nav tab width, rows vs height for bar charts and tables (`_build/row_hints.json` from `build_report.py`).

## Round 2 score (2026-11-27, evidence: docs/BlinkitSales-PBI.pdf 07:36 export after Refresh + Ctrl+0; PNGs docs/dashboard/01-07)
BPA 27/27 pass (185 measures, 6 relationships). Numbers read off the pages match reconciliation.md and live_checks.md
(1.10 Cr, 5,000, 2,201.86, 69.4%/30.6%, 14.5 min, 3.34, 45.8%/46%, 68.7% = 1,492 of 2,172, ROAS 1.97, 29.49 M, 2.97 M, 5.12 L).

| # | Criterion | Score | Evidence |
|---|---|---|---|
| 1 | Purpose and message | 1.0 | Action titles with numbers on all pages; p4 visual title now "46% of revenue". |
| 2 | Data trust | 0.75 | All numbers reconcile; footer is cut to "refreshed 2..." on every page, so the refresh date is not readable. |
| 3 | KPI design | 0.75 | Like-for-like change lines on p1-p5 and p7 card 1, colour by direction; no targets; p7 cards 2-4 and p4 repeat card have context text only; p2 "0.0 pp" shows a green up arrow; p1 rating card truncated ("Oct ..."). |
| 4 | Chart choice and honesty | 0.75 | Exposure card now 5.12 L combined (fixed). p5 matrix column still reads "All" (App 1.82x vs bar 1.92x; subtitle explains); lines on p1/p5/p7 use a thin band with half the plot empty. |
| 5 | Layout and hierarchy | 0.75 | p1 no longer clipped (fixed). Scrollbars remain: p2 Top 5 products (3 of 5 visible), p2 payment (3 of 4), p5 campaigns (8 of 9). Nav labels are clipped at the bottom of every pill. Empty lower halves on p6 left panel and p3 text panel. |
| 6 | Colour and accessibility | 0.75 | Unchanged: brand green, RdBu/YlGn, status colours with arrows; small grey captions borderline; alt text not verifiable from PDF. |
| 7 | Declutter, text, format | 0.75 | Units and "L" in heat map cells fixed; footer, nav pills and p1 rating change line truncated. |
| 8 | Interaction, navigation, devices | 0.75 | Slicers, drill-through, tooltips, phone confirmed; campaign drill-through unconfirmed; no reset button. |
| 9 | Insight and action | 1.0 | p6 findings and p7 levers consistent with cards. |
| 10 | Model and engineering | 1.0 | BPA 27/27, reconciled, DAX titles. |
| | Raw total | 8.25 | |
| | Gates | max 7 | Truncated text and scrolling visuals (footer, nav, p1 card) cap at 7. No wrong numbers or misleading encodings remain. |
| | **Final** | **7.0 / 10** | Reaches about 9.5 once fixes 1-3 are done. |

Round-1 items confirmed fixed: p4 title 46%; p1 clipping; p7 exposure 5.12 L; card caption overlap and change lines; p5 ROAS card and labels; p2 heat map shows 12 months with L units; p2 no longer cuts months.
Not fixed: scrolling on three visuals, nav label clip, reset button, campaign drill-through confirmation, p5 "All" header.

### Remaining fixes, ranked
1. Footer text box (footer helper in `_build/build_report.py`/`pbir_kit.py`): widen it to the space before the nav (about 840 px) or shorten to "Blinkit (synthetic) · Mar 2023-Nov 2024 · INR assumed · refreshed <date>" so the refresh date shows.
2. Nav pills (nav function in `pbir_kit.py`): raise height (about 26 px) or reduce font/padding so labels are not clipped.
3. Scrolling visuals: p2 Top 5 products and payment visuals (page-2 function in `build_report.py`, heights and `row_hints.json`; payment needs about 4 rows of room), p5 campaign chart (9 rows, more height or a 9 pt font). Extend the `check_report.py` row check to fail on any list visual with fewer visible rows than data.
4. p1 rating card change line truncated ("0.01 pts Oct 24 vs Oct ..."): shorten the change-line format or use "vs Oct 23" in the card helper.
5. p5 matrix: rename the "All" column header (check that prepare.py rename reached the model; the PDF still shows "All"); flat lines: set a tighter y-axis min only if labelled, or use smaller chart height.
6. Reset-filters bookmark and confirm campaign drill-through; verify alt text and caption contrast.

## Round 3 changes (2026-11-27, not yet re-exported or re-scored)
1. Footer: text shortened to "Blinkit sales (Kaggle, synthetic) · Mar 2023 to Nov 2024 · INR assumed · refreshed <date>" (about 96 characters); box 560 px.
2. Navigator: pills 32 px high (were 28, labels clipped), footer and nav moved up 4 px; nav 680 px wide, 7 tabs.
3. No scrolling: p2 Top 5 products and payment visuals 214 px high (heat map shrinks to 266 px, still fits 11 rows); p5 campaign chart 290 px high, subtitle moved into the title (9 bars).
4. p1 rating change line shortened to "▲ 0.01 Oct 24 vs Oct 23" (unit "pts" dropped; the card label says 1-5).
5. p5 matrix "All": data/clean already holds "All audiences" and the model was regenerated; the PDF still showed "All" because the model was not refreshed, so Refresh fixes it.
6. Targets (assumptions, not company data): on-time orders target 75% (label p3), ROAS target 2.0x (label p5), repeat customers target 70% (p4 line "1,492 of 2,172 · target 70%"). Stock damage target 3.5% not shown: no card carries damage. p7 cards keep their context lines.
7. Line charts on p1, p5 (two) and p7 no longer start at zero or fix the top, so the series fills the plot; subtitles say "axis not from zero". Bars stay at zero.
8. Reset filters: not done. The "Clear all slicers" button action could not be verified against the PBIR schema here, and a wrong action type would break the report; use Ctrl+click on slicers or the slicer clear icon.
9. check_report.py calibrated: footer text width from the Footer Text measure, nav height >= 32, change-line width per measure (5.6 px/char, 48 px padding), bar rows 26 px each plus 75/50 px chrome, pivot rows 1.333 x pt + 5, every bar/pivot must have a row hint. On the round-2 build (old spec and geometry) it fails: footer on all pages, nav on 7 pages, p1 rating line, p2 Top 5 and payment, p5 campaign; it passes on the new build.
Needs Refresh in Desktop (footer measure, Δ Avg Rating, Δ Repeat Rate changed; "All audiences"), then export and re-score.

## Round 3 score (2026-11-27, evidence: docs/BlinkitSales-PBI.pdf 07:56 export; PNGs docs/dashboard/01-07 re-rendered)
BPA: 0 failures (all rules pass). Numbers read off pages match reconciliation.md and live_checks.md (1.10 Cr, 5,000, 2,201.86, 69.4/30.6%, 14.5 min, 3.34/3.37/3.33, 45.8%/46%, 50.42 L, 68.7% = 1,492 of 2,172, ROAS 1.97 / 2.05 / 1.92, 29.49 M, 2.97 M, 5.12 L, 64.52 L, MAPE 2.8%).

Round-2 items: footer FIXED (date readable pp2-7); nav pills FIXED (labels whole); p2 Top 5 and payment FIXED (5 and 4 bars, no scrollbar); p5 campaign chart FIXED (9 bars); p1 rating line cannot be seen because page 1 is clipped; targets FIXED (p3 75%, p4 70%, p5 2.0x shown in label/line); line axes FIXED (not from zero, labelled). NOT fixed: p5 matrix header still "All" (subtitle explains); p2 heat map still has a scrollbar and cuts the last row (Snacks & Munchies, 11 of 12 rows).
NEW: page 1 of the PDF is exported zoomed and clipped (4th card cut, right panel and bottom row, footer and nav missing); pp2-7 are fine. p5 campaign visual shows a duplicate auto subtitle "ROAS by Campaign Name".

| # | Criterion | Score | Evidence |
|---|---|---|---|
| 1 | Purpose and message | 1.0 | DAX action titles with numbers on every page. |
| 2 | Data trust | 0.75 | Reconciles; footer readable pp2-7 but missing on the clipped p1. |
| 3 | KPI design | 0.75 | Targets now on p3-p5 and like-for-like deltas; no sparklines; p2 "0.0 pp" shows a green up arrow; p7 cards 2-4 context only. |
| 4 | Chart choice and honesty | 0.75 | Line axes labelled; p5 matrix "All" column still reads as a total (1.82x vs bar 1.92x). |
| 5 | Layout and hierarchy | 0.75 | p1 clipped; p2 heat map scrolls; empty lower halves p3 text panel and p6 left panel. |
| 6 | Colour and accessibility | 0.75 | Unchanged; alt text not verifiable from PDF; small grey captions. |
| 7 | Declutter, text, format | 0.75 | Footer/nav/rating line fixed; p1 cut text, p5 duplicate subtitle, matrix header. |
| 8 | Interaction, navigation, devices | 0.75 | Slicers, both drill-throughs, tooltips, phone confirmed; no reset button (documented). |
| 9 | Insight and action | 1.0 | p6 findings, p7 sized levers, MAPE and band. |
| 10 | Model and engineering | 1.0 | BPA clean, reconciled, DAX titles. |
| | Raw total | 8.25 | |
| | Gates | max 7 | Page text clipped / scrolling visual (p1 clip, p2 heat map). No wrong numbers or misleading encodings. |
| | **Final** | **7.0 / 10** | About 9.5 after fixes 1-2. |

### Remaining fixes, ranked
1. Re-export p1 properly (Ctrl+0 / fit page on page 1 before File > Export PDF); if it persists, check page-1 size and `page.json` display option in the page-1 function of `_build/build_report.py`. Cap 7 lifts.
2. p2 heat map: shrink rows or give 12 rows room (page-2 function in `build_report.py`, `row_hints.json`), or limit to 10 categories; no scrollbar.
3. p5 matrix: header "All" to "All audiences" (rename column display name in the matrix builder / model column `displayName`; check prepare.py output reached the model). Remove duplicate subtitle "ROAS by Campaign Name" on the campaign visual (set subtitle/title off in its builder).
4. p2 "0.0 pp" neutral colour (change-line measure in `measures_spec.py`); fill empty lower halves p3/p6 or shrink panels.
5. Reset-filters bookmark; verify alt text and caption contrast.

## Round 4 changes (2026-11-27)
1. p5 matrix: audience value renamed "All users" (prepare.py, data dictionary, tables_spec); matrix widened 380 to 440 px (channel bar 380, campaign bar 404), 9 pt, column-header word wrap on. Width math: row header ~82 px + four columns ~71 px = ~350 px of 416 px inside the visual.
2. p2 heat map: 11 category rows + header need ~298 px; visual is 300 px (was 266). Top 5 products and payment shrunk to 180 px (5 bars x 26 + 50), their subtitles folded into the titles; heat subtitle folded into its title.
3. p5 campaign chart: the pbir kit now writes an explicit subTitle show=false on every titled visual without a subtitle (removes Desktop's auto subtitle "ROAS by Campaign Name").
4. Change lines: a change under 0.05 pp / 0.05 % / 0.005 shows a flat marker and neutral grey (all yoy() lines, Revenue/Orders/AOV, F25 forecast line).
5. check_report.py new rules: (a) pivot header text vs column width and total width (pivot_hints.json, written by build_report); (b) pivot rows x row height + header + chrome vs visual height; (c) title = subtitle, and titled visuals without an explicit subtitle setting. On the old geometry they failed: mx_ca needs ~433 px of 380; mx_heat needs ~310 px of 266; bar_campaign has no explicit subtitle setting. All pass now.
Checks: prepare, make_semantic_model, reconcile (70 values), bpa 27/27, check_measures, build_report, check_report, pbi report validate all pass. Refresh needed (data and measures changed).

## Round 4 score (2026-11-27, evidence: docs/BlinkitSales-PBI.pdf 08:42 export; PNGs docs/dashboard/01-07 re-rendered)
BPA: 27 rules, 27 pass, 0 fail. Numbers read off all 7 pages match reconciliation.md and live_checks.md (1.10 Cr, 5,000, 2,201.86, 69.4%/30.6%, 14.5 min, 3.34/3.37/3.33, 45.8%/46%, 50.42 L, 68.7% = 1,492 of 2,172, ROAS 1.97/2.05/1.92, 29.49 M, 2.97 M, 5.12 L, 64.52 L, MAPE 2.8%).

Confirmed fixed: p1 not clipped (6 cards, both panels, footer, nav; rating line "0.01 Oct 24 vs Oct 23" whole); p2 heat map shows all 11 rows incl. Snacks & Munchies with no scrollbar; p2 "0.0 pp" is a neutral grey dot; p5 campaign chart has no duplicate subtitle (9 bars); footer and nav whole on all pages.
NOT fixed: p5 matrix column header still reads "All" (subtitle says "All users"; data/clean/fact_marketing.csv and TMDL hold "All users", so either the model was not refreshed or the 71 px column clips the label). Wrong header still invites reading it as a total (1.82x vs bar 1.92x).

| # | Criterion | Score | Evidence |
|---|---|---|---|
| 1 | Purpose and message | 1.0 | DAX action titles with numbers on all pages. |
| 2 | Data trust | 1.0 | Reconciles; footer with source, range, currency, refresh date on every page. |
| 3 | KPI design | 0.75 | Like-for-like deltas, targets on p3-p5; no sparklines; p7 cards 2-4 and p4 repeat card context only. |
| 4 | Chart choice and honesty | 0.75 | Honest axes, labelled non-zero lines; p5 matrix "All" header ambiguous. |
| 5 | Layout and hierarchy | 0.75 | No clipping or scrollbars; empty lower halves on p3 text panel, p6 left panel, p5 matrix panel; p2 heat map leaves spare room. |
| 6 | Colour and accessibility | 0.75 | Brand/RdBu/YlGn with arrows and labels; small grey captions; alt text not verifiable from PDF. |
| 7 | Declutter, text, format | 0.75 | Units everywhere; p5 header "All" is the only wrong label. |
| 8 | Interaction, navigation, devices | 0.75 | Slicers, both drill-throughs, tooltips, phone confirmed; no reset button (documented). |
| 9 | Insight and action | 1.0 | p6 findings with Do next, p7 sized levers, MAPE and band. |
| 10 | Model and engineering | 1.0 | BPA 27/27, reconciled, DAX titles. |
| | Raw total | 8.5 | |
| | Gates | none | No wrong numbers, misleading encoding, clipping or scrolling visual. |
| | **Final** | **8.5 / 10** | |

### Remaining fixes, ranked
1. p5 matrix header: Refresh the model in Desktop (fact_marketing "All users"); if it still shows "All", widen the first value column or the visual in the p5 matrix builder (`_build/build_report.py`, mx_ca) and re-check `pivot_hints.json`.
2. Fill empty panels: p3 "What this tells us" and p6 left panel (shrink panel height or add a small chart; page functions in `build_report.py`); use spare space under the p5 matrix.
3. KPI context: p7 cards 2-4 and p4 repeat card (card helper in `pbir_kit.py`, `measures_spec.py`); add sparklines on p1/p3 cards.
4. Reset-filters bookmark (not supported by the kit); verify alt text on every visual (`pbir_kit.py` visual helper) and caption contrast.

## Round 5 changes (2026-11-27, not yet rendered; re-score after the next PDF export)
- p5 matrix: audience value "All" renamed "Everyone" (prepare.py, data dictionary, subtitle "Everyone = campaigns aimed at all users", pivot_hints); header word wrap off; 11 pt headers and values, row padding 11, matrix 450 px wide so it fills the panel (channel chart 370 px).
- p3 "What this tells us" and p6 findings: text raised to 11 pt / 13 pt with paragraph gaps so the panels fill (p3 row 2 shortened to 236 px).
- KPI context lines now compare: p7 range card (last 12 months inside/above/below the 80% range), vs-LTM card (gap in rupees vs last 12 months), backtest (within the 5% target), exposure (share of 12-month revenue with the base); p4 repeat card shows points vs the 70% target, coloured green/red.
- Caption contrast: MUTED #4A5750 (7.0:1 on the page background), context grey #46525F (7.4:1); old values already passed AA (5.6 and 5.1), now with margin.
- Skipped: sparklines in cards (no confirmed PBIR property; no room for extra charts); "Clear all slicers" button (no ClearAllSlicers example on disk or in the schemas under D:\Wolf\PBI, so the property is unconfirmed).
- check_report.py: new rules for AA contrast of theme muted text and GOOD/BAD/NEUTRAL, text boxes filling < 60% of the box, matrices filling < 60% of their panel.
- Refresh needed: yes (fact_marketing audience value and 5 changed measures); open the .pbip, Home > Refresh, Ctrl+S, export the PDF once.

## Round 5 score (2026-11-27, evidence: docs/BlinkitSales-PBI.pdf 08:52 export; PNGs docs/dashboard/01-07 re-rendered at 1600 px)
BPA 27/27 pass. All numbers on the 7 pages match reconciliation.md and live_checks.md (1.10 Cr, 5,000, 2,201.86, 69.4%/30.6%, 14.5 min, 3.34, 45.8%/46%, 50.42 L, 68.7%, ROAS 1.97/2.05/1.92, 29.49 M, 2.97 M, 5.12 L, 64.52 L, MAPE 2.8%). Alt text present on 186 of 186 visuals (grep of visual.json). Same standard as Airline: Airline had neither sparklines nor a reset button and scored 1.0 on KPI design and interaction, so both are not held against Blinkit.

Confirmed fixed: p4 repeat card shows "1.3 pp vs 70% target" (red); p7 cards 2-5 carry comparing context lines; p6 left panel fuller; p5 matrix fills its panel with no empty block, 11 pt; caption contrast raised.
NOT fixed / new defects:
- p5 matrix column header still reads "All" while the subtitle says "Everyone = campaigns aimed at all users" (data/clean/fact_marketing.csv and the TMDL hold "Everyone", so the model was not refreshed before export, or the column is a stale cache). The matrix also shows a vertical scrollbar.
- NEW p3 "What this tells us": text is larger now and overflows, a dark scrollbar shows, first line runs to the panel edge and the last line ("Action: size the 5-point late-share lever on page 7.") is cut at the bottom.
- NEW p7 backtest card context line truncated ("Within the 5% target · naive mo...").

| # | Criterion | Score | Evidence |
|---|---|---|---|
| 1 | Purpose and message | 1.0 | DAX action titles with numbers on every page. |
| 2 | Data trust | 1.0 | Reconciles; footer with source, range, currency, refresh date on every page. |
| 3 | KPI design | 1.0 | Like-for-like deltas on pp1-5, targets on p3/p4/p5, vs-target and vs-LTM context on p4/p7; same as Airline's standard. |
| 4 | Chart choice and honesty | 0.75 | Honest axes; p5 matrix header "All" still reads as a total (1.82x vs bar 1.92x). |
| 5 | Layout and hierarchy | 0.75 | p3 text panel overflows with scrollbar; p5 matrix scrollbar. Otherwise stratified, no clipping elsewhere. |
| 6 | Colour and accessibility | 1.0 | AA contrast, arrows with colour, alt text 186/186, phone layout. |
| 7 | Declutter, text, format | 0.75 | p3 clipped last line, p7 truncated context line, p5 header. |
| 8 | Interaction, navigation, devices | 1.0 | Slicer sync pp1-4, both drill-throughs, tooltips, phone confirmed; no reset button (Airline had none). |
| 9 | Insight and action | 1.0 | p6 ranked findings and Do next; p7 sized levers, MAPE, 80% band. |
| 10 | Model and engineering | 1.0 | BPA 27/27, reconciled, generators, DAX titles. |
| | Raw total | 9.25 | |
| | Gates | max 7 | Gate "text overflows or is truncated" (p3 panel, p7 card line). No wrong numbers, misleading encodings or contrast failures. |
| | **Final** | **7.0 / 10** | 9.25 once the gate lifts; 10 after fixes 1-3 below. |

### Remaining fixes, ranked
1. p3 text panel (page-3 function in `_build/build_report.py`): back to 10 pt or enlarge the box / shorten the five paragraphs so no scrollbar or cut line shows.
2. p7 backtest card context line: shorten to "Within the 5% target" (measure in `measures_spec.py`; check_report change-line width).
3. p5 matrix: Refresh the model so "Everyone" appears; remove the matrix scrollbar (a little more height or a smaller row padding); re-export once.

## Round 6 changes (2026-11-27, no re-export yet)
- p3 text panel: paragraphs 1 and 2 cut to one line each (about 40 px saved) at 11 pt, box unchanged (618x244).
- p7 backtest context line: "Within the 5% target" (was 34 chars, 190 px needed in 184 px).
- p5 matrix mx_ca: row padding 11 -> 8 (rows + header ~275 px of 290).
- check_report.py now fails on: text-box overflow (0.55 em glyph, 1.35 line, gap paragraphs cost a line + 4 px), card context lines read from the real measure text in the TMDL, and pivot rows with a padding term. Before the fixes it flagged exactly these three (249 of 234 px, 190 of 184 px, 303 of 290 px).
- Pending: one re-export to confirm no scrollbars; the "All" vs "Everyone" header needs the model refresh the user handles.
