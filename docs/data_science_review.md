# Data science review: BlinkitSales

Generated from `analysis/ds_review.py` (numbers in `docs/ds/results.json`, charts in `docs/ds/`). Data: `data/clean/*.parquet`, plus `store_id` and `delivery_partner_id` from `data/raw` (counts only). No personal fields were read. Amounts in assumed INR.
Tools: Python, pandas 3.0.3, scipy 1.18, statsmodels 0.14.6 (OLS, ordered logit, Cox PH, ANOVA), scikit-learn 1.9 present but not needed. `lifelines` was not used; Cox models come from statsmodels `PHReg`.

## 0. Read this first: the data behave like a random generator

An expert would stop after the diagnostics, because most relationships a real business has are absent here.

| Diagnostic | Result | What real data looks like |
|---|---|---|
| Orders per customer, variance vs mean | var 1.56 vs mean 2.30 (under-dispersed; random assignment gives 2.30) | Over-dispersed, a heavy tail of heavy buyers |
| Revenue Gini across customers | 0.366 vs 0.361 when orders are assigned to customers at random | 0.6 to 0.8 |
| Top 20% of customers' revenue share | 40.9% (top 10%: 24.0%) | 60 to 80% |
| Cohort retention M+1 to M+6 | flat 8 to 10% | decays |
| Hour of day uniform? | chi-square p = 0.19 (max/min 1.33) | evening and morning peaks |
| Day of week uniform? | p = 0.85 | weekend lift |
| Order total vs quantity x unit price | r = -0.008 | about 1 |
| Discount depth (15 to 40% off MRP) vs quantity | Spearman 0.006 (p = 0.66) | negative or positive, but present |
| Distance vs minutes late | Spearman 0.004 (p = 0.77) | clearly positive |
| Marketing revenue vs spend | elasticity -0.01 (p about 0.35) | positive, concave |
| Store and rider IDs | 5,000 distinct values in 5,000 orders | repeat many times |
| Orders before the customer's registration date | 51% | near 0% |
| Marketing spend vs order revenue | spend ₹1.63 Cr vs order revenue ₹1.10 Cr; attributed revenue 2.9x orders | spend below revenue |

So every "null" below is more likely a property of the generator than a fact about Blinkit. Recommendations are therefore framed as hypotheses to test on real data, not as findings to act on.

## 1. Questions, methods, results

### A. Customers

**A1. Do the stored segments differ in value?** Kruskal-Wallis and eta-squared by customer. Orders per customer p = 0.98, revenue per customer p = 0.61, eta² = 0.0013. Order-level AOV differs slightly (p = 0.027; New ₹2,288 vs Premium ₹2,154, about 6%), which is one test of about ten and does not survive a Bonferroni correction. Null. So what: stored `segment` has no behavioural meaning; do not target on it.

**A2. Repeat vs one-time?** 68.7% of 2,172 customers ordered 2+ times and they hold 86.7% of revenue. A random assignment of the 5,000 orders to the same customers gives 66.9%, so the repeat rate carries no loyalty information. So what: the 68.7% is a base-rate artifact.

**A3. Cohort retention by first-order month.** Share of each cohort ordering again k months later: M+1 8.5%, M+2 9.4%, M+3 8.2%, M+4 9.8%, M+5 9.0%, M+6 8.3% (cohorts of 5 to 233 customers; the first and last months are partial). Flat, no decay, no maturation. See `docs/ds/cohort_retention.png`.

**A4. Time to second order.** Median gap between consecutive orders 111 days (mean 144, P90 319); time to the second order 134 days (n = 1,492). So what: the reorder cycle is long for groceries, so a "60-day reorder" metric is a harsh one on this data; use it consistently.

**A5. RFM.** Tercile scores, simple labels: Champions (355 customers, 27.5% of revenue, 3.9 orders each), Loyal-but-lapsing (369, 27.0%), Middle (917, 34.3%), Lost-light (398, 8.4%), Recent-light (133, 2.8%). So what: behavioural RFM gives usable groups (54.5% of revenue from 33% of customers), but with random orders these groups are partly mechanical; re-test on real data.

**A6. Concentration (Pareto).** Top 10% of customers = 24.0% of revenue, top 20% = 40.9%, Gini 0.366, equal to the random-assignment Gini 0.361. See `docs/ds/pareto.png`. Null.

### B. Basket and price

**B1. Does discount depth change quantity or order value?** Discount = 1 - price/MRP, mean 27.7% (15 to 40%). Spearman with quantity 0.006 (p = 0.66), with order total -0.015 (p = 0.29); quantity is uniform 1/2/3 (33/33/34%). Null. Also `order_total` is unrelated to `quantity x unit_price` (r = -0.008), so the basket cannot explain revenue.

**B2. Category mix by segment, area, payment.** Chi-square with Cramér's V: segment p = 0.16 (V 0.05), payment p = 0.75 (V 0.04), area p = 0.46. Area has 316 levels for 5,000 orders, so V = 0.25 is a small-cell artifact. Null; AOV by category (p = 0.86), by payment (₹2,183 to ₹2,230, p = 0.76) also null.

**B3. Hour and weekday patterns.** Order counts by hour: chi-square p = 0.19 (busiest 8h, 13h, 19h, within sampling noise); by weekday p = 0.85; AOV by hour p = 0.36, by weekday p = 0.36. Null. So what: do not schedule staff or promotions by hour from this data.

### C. Delivery

**C1. What drives minutes late?** OLS with HC3 errors on distance, hour, weekday, area (316 levels) and category: R² 0.064 but adjusted R² -0.008, i.e. nothing beyond noise. Distance: +0.05 min/km (95% CI -0.14 to +0.24, p = 0.64), standardized effect 0.007 SD. Type-II ANOVA p: hour 0.51, weekday 0.81, area 0.92, category 0.60. Minutes late is also near-uniform (histogram max/min 12.6, range -5 to 30). Null.

**C2. On-time by area, distance.** Late rate 30.6% (Wilson 95% CI 29.3 to 31.9%). Logistic odds ratio per km 1.003 (0.96 to 1.05, p = 0.89); late rate by distance tercile 31.3 / 29.6 / 30.9%. By area chi-square p = 0.45 (the 0 to 100% range across areas is small-sample noise: smallest area has 1 order), hour p = 0.30, weekday p = 0.89, category p = 0.20. Null. So what: promised times appear unrelated to distance; on real data, an ETA that ignores distance would be the first thing to check.

### D. Experience

**D1. Does delay predict rating?** Late vs on-time mean rating difference +0.039 (bootstrap 95% CI -0.029 to +0.107), Cohen's d 0.03; Kruskal by status p = 0.55; Spearman(rating, minutes late) -0.008. Ordered logit of rating on minutes late, distance, payment, segment, category (18 terms): none significant at 5% (smallest p = 0.11); OR per extra minute late 0.9986 (0.992 to 1.005). Null.

**D2. Do payment, segment, category predict rating?** Kruskal p: payment 0.78, segment 0.79, product category 0.41, feedback category 0.57. Null. Negative sentiment vs minutes late: OR 1.004 per minute (p = 0.24).

**D3. What do feedback categories say?** Four categories, evenly split (25.4% Delivery, 25.3% Customer Service, 25.0% Product Quality, 24.3% App Experience). Feedback category is unrelated to delivery status (chi-square p = 0.22, V 0.03) and to sentiment (p = 0.61): orders tagged "Delivery" are late 28.1% of the time vs 31.5% for others. Sentiment is a deterministic function of rating (1-2 Negative, 5 Positive, 3 and 4 mixed; V 0.74), so it adds no information. Feedback text is 25 template sentences. So what: category tags do not describe the cause of the complaint.

**D4. Does a bad experience reduce the next order? (key question).** Unit: order; "poor" = late or rating 1-2 (45.8% of orders). Orders with 60+ days of follow-up (n = 4,507): 60-day reorder rate 18.4% after a good experience vs 16.9% after a poor one (-1.5 points). Logistic, customer-clustered SEs: OR 0.90 (95% CI 0.77 to 1.05, p = 0.19); late alone OR 0.96 (0.82 to 1.14, p = 0.66); rating 1-2 alone OR 0.89 (0.73 to 1.09, p = 0.27). Time to next order, Cox PH with censoring at the last date: all orders HR 0.96 (0.89 to 1.03, p = 0.24); first order only (n = 2,172, independent) HR 0.94 (0.85 to 1.04, p = 0.21). The direction is the expected one, but the effect is not distinguishable from zero, and the CI allows up to about a 23% cut in reorder odds. This is a null result with real uncertainty, not evidence of no effect. It also cannot be causal: experience is not randomized and customers are not tracked beyond the data window.

### E. Marketing

**E1. ROAS distribution.** Overall ROAS 1.97 (bootstrap 95% CI 1.95 to 2.00). Row-level ROAS mean 2.38, median 1.97, 5th to 95th percentile 0.69 to 5.70; 14.6% of rows are below 1.0. Always aggregate as SUM/SUM.

**E2. Channel x audience differences.** Channel ROAS: Email 2.05 (1.99 to 2.11), SMS 1.99, Social 1.94, App 1.92 (1.86 to 1.97); Kruskal on row ROAS p = 0.007, two-way ANOVA channel p = 0.014, audience p = 0.084, interaction p = 0.40. The gap Email vs App is 0.13 (about 7%), with overlapping intervals once 16 cells are compared: only 1 of 16 channel x audience cells has a CI excluding the overall ROAS (expected by chance about 0.8). Audiences 1.94 to 1.99, p = 0.53. Weak, small, unlikely to be actionable; see `docs/ds/roas_ci.png`.

**E3. Diminishing returns.** Log-log regression of attributed revenue on spend: elasticity -0.013 (95% CI -0.040 to +0.014, R² 0.0002); Spearman spend-revenue -0.013 (p = 0.32). Revenue per row is independent of spend, so ROAS falls mechanically with spend (by spend quintile 4.26, 2.63, 1.97, 1.59, 1.27; Spearman spend-ROAS -0.68). The apparent "diminishing returns" is a ratio artifact, not a response curve; the true marginal return implied is about zero. See `docs/ds/spend_revenue.png`.

**E4. Funnel.** CTR 10.1%, click-to-conversion 10.0%, cost per conversion ₹54.8, attributed revenue per conversion ₹108. Conversions vs revenue Spearman -0.011; conversion rate vs ROAS 0.004. CTR vs conversion rate -0.48 is mechanical (clicks sit in both ratios). The funnel does not link to revenue. Also 59.6 conversions per order, which is not credible.

### F. Inventory

**F1. Damage by category and product.** Overall 3.85%. By category 3.1% (Pharmacy) to 4.65% (Household Care), chi-square p = 0.24. Product-level SD 0.0184 vs 0.0187 expected from pure binomial noise, so there is no real product heterogeneity; shelf life vs damage Spearman 0.013 (p = 0.83). Null. Damaged stock is worth about ₹5.3 L at list price over the period.

**F2. Received stock vs sales velocity.** Received 28,779 units vs 10,034 sold in the order data (2.9x; product median 2.9, P10 to P90 2.1 to 4.2). Spearman received vs sold: product-month 0.05 (p < 0.001, but tiny), product 0.09 (p = 0.15). Inbound stock is not tied to demand; the 2.9x gap probably reflects that the orders file is a sample, so treat it as a mismatch indicator only.

### G. Forecasting

**G1. Trend and seasonality?** 19 full months. Linear trend -₹2,096/month (95% CI -4,693 to +501, p = 0.11; Kendall tau -0.32, p = 0.058; R² 0.15); at 5.6% coefficient of variation the series is stationary (ADF p = 0.001) and white-noise-like (Ljung-Box lag 6 p = 0.85). Seasonality: 7 month-pairs with YoY mean -4.2% (p = 0.14); lag-12 correlation 0.32 on 7 pairs; day-of-week p = 0.42. No detectable trend or seasonality; 19 points cannot rule out a modest decline.

**G2. Forecast uncertainty.** One-step rolling backtest (origin from month 10): MAPE naive 4.0%, expanding mean 4.7% (differs from the 2.77% in `reconciliation.md`, which uses a different 6-month window; either is small). 95% prediction interval for any single month: mean model ±₹62k (±11% of ₹5.61 L), naive ±₹88k (±16%); rolling coverage of the mean-model interval 11 of 11. Forecast rule: flat line ₹5.4 to 5.6 L a month with a ±11% band, and never publish a point forecast without it. See `docs/ds/monthly_revenue.png`.

## 2. What the nulls mean

Between synthetic generation and a 5,000-order sample, only these things hold: sentiment is a function of rating; revenue, marketing and delivery columns are independent draws; the repeat rate is a base rate. Strategy statements need real data. The report's "levers" (₹5.12 L from delay and rating) assume a delay-to-outcome link that this data does not support (D1, D4), so treat them as scenarios.

## 3. Recommendations (illustrative sizing, annual, assumed INR)

Basis: revenue last 12 full months ₹66.6 L, about 3,000 orders at AOV ₹2,202, marketing spend about ₹99.5 L a year. Scores 1 to 5 (5 = best; effort 5 = cheapest); priority = impact x confidence x effort. All values are illustrative, produced on data that behave like a random generator.

| # | Recommendation | Evidence | Annual size (illustrative) | Impact | Conf. | Effort | Priority |
|---|---|---|---|---|---|---|---|
| 1 | Run a marketing incrementality test (geo or customer holdout), then reallocate | Revenue unrelated to spend (elasticity -0.01), spend above order revenue | each 10% of spend that proves non-incremental = ₹9.9 L | 5 | 3 | 3 | 45 |
| 2 | Win-back nudge for lapsing customers around day 90 (median gap 111 days) | Reorder cycle long; 31% never repeat | +3 pts 60-day reorder = about 90 orders = ₹2.0 L | 3 | 3 | 4 | 36 |
| 3 | Fix data capture (item lines, store and rider IDs that repeat, cost, attribution IDs) | Nothing can be tested without them | option value, no ₹ sizing | 4 | 5 | 3 | 60 |
| 4 | Discount-depth test (cut 2 pts of MRP discount in a few categories) | Depth 15 to 40% has no link to quantity | about ₹0.8 L margin if volume holds (line value basis) | 2 | 2 | 4 | 16 |
| 5 | Calibrate promised ETA to distance and test it | Late rate flat across distance (30.6% everywhere) | reorder link: point ₹0.5 L, upper ₹1.2 L (CI of D4); the ₹2.64 L lever assumes a link not seen | 2 | 2 | 3 | 12 |
| 6 | Align inbound stock to sales velocity; track damage by product with real batch data | Received/sold 2.9x, damage 3.85% = ₹5.3 L over the period | damage cut 0.5 pt = ₹0.4 L (reconciliation lever) | 2 | 2 | 3 | 12 |
| 7 | Replace stored segments with behavioural RFM in CRM | Stored segment null; RFM groups 54.5% of revenue from 33% of customers | targeting efficiency, not sized | 2 | 3 | 4 | 24 |

Priority order: 3, 1, 2, 7, 4, 5/6. Recommendation 3 comes first because it unlocks the rest; recommendations 1 and 2 are the experiments below.

## 4. Experiment design for the top two tests

All sample sizes: two-sided α = 0.05, power 0.8, equal arms, observed variance from this data.

**Experiment 1: marketing incrementality holdout.**
- Hypothesis: spend on the highest-spend quintile of campaign-days produces no extra revenue vs a holdout.
- Unit: campaign-day record (here) or customer / geo cell in real data. Metric: incremental revenue per unit (primary), orders per customer as guardrail.
- Observed mean ₹5,962 per record, SD ₹2,322 (ROAS SD 1.56).
- MDE 10% of revenue per unit: 239 units per arm. MDE 5%: 953 per arm. For ROAS, MDE 0.2 needs 955 per arm and MDE 0.1 needs 3,818 per arm.
- Duration: with 5,400 records in about 20 months (270 a month), a 5% MDE needs about 7 months of pooled campaign-days; a customer or geo holdout on real data should reach it in weeks.
- Decision rule: if the CI of incremental ROAS includes 0 and the upper bound is under 1.0, cut that spend by 10 to 20% and repeat.

**Experiment 2: lapsing-customer win-back nudge.**
- Unit: customer (randomize once, avoids the order-level clustering seen in D4). Eligible: customers with no order for 90 days.
- Metric: 60-day reorder rate. Baseline 17.75%. Guardrails: AOV, unsubscribe rate, discount cost per reorder.
- MDE +2 pts: 5,975 per arm; +3 pts: 2,708; +5 pts: 1,011. AOV alternative: 5% MDE = 2,199 per arm, 10% = 550 per arm (SD ₹1,303).
- Feasibility: this data has 2,172 active customers, so a 1,086-per-arm split has an MDE of about +4.8 pts, so run it with the real customer base (about 10x here) or accept only large effects.
- Analysis: two-proportion z-test plus Cox PH for time to next order, pre-registered.

## 5. Data we would need

1. Order items: more than one item per order (here one line per order, so basket analysis, affinity and cross-sell are impossible), and order totals that reconcile with item lines.
2. Store and rider IDs that repeat (here 5,000 unique IDs in 5,000 orders): store capacity, rider productivity and fixed-effects models.
3. Cost data: delivery cost per order, COGS, funding of discounts, so margin and profit per order replace revenue.
4. Attribution IDs linking campaigns to orders and customers (here marketing has no key to orders and revenue is 2.9x order revenue), with a holdout flag.
5. Real timestamps for promise, dispatch, pickup and delivery, and ETA shown at checkout; plus customer lat/long and store lat/long to compute distance independently.
6. Customer tenure and acquisition source with a reliable registration date (51% of orders precede it), consent flags and app sessions for funnel analysis.
7. Inventory: daily on-hand, stock-outs, waste reasons and batch expiry, so lost sales and waste can be separated.
8. Longer history (24 months or more, full months only) for seasonality and cohort maturity, plus festival and weather calendars.

## 6. Reproduce

`python analysis/ds_review.py` (about a minute, writes `docs/ds/results.json` and 5 PNGs: cohort retention, Pareto, ROAS CIs, spend vs revenue, monthly revenue with band).
