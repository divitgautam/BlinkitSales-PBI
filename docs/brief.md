# BlinkitSales-PBI: brief and page plan (Phase 1, 2026-11-27)

> **Decision (2026-11-27):** revenue = `order_total`; item lines appear only as "Line value" for category mix.

Evidence: `docs/audit.md` (rerun with `python _build/audit.py`). Playbook: `D:\Wolf\PBI\_knowledge\dataviz_playbook.md`.
Workflow: `D:\Wolf\PBI\powerbi-modelling-mcp\docs\WORKFLOW.md` (R1 reconcile first, R2 generate model and report, R4 DAX title measures).

## Context (SWD step 1)
- **Reader:** a quick-commerce sales and operations leader (category and city ops head) reviewing performance weekly or monthly on a laptop screen.
- **Decision:** where to push assortment, where delivery slips, and whether marketing spend earns its keep.
- **Big idea (one sentence):** Blinkit sells about the same basket every month across 11 categories, one delivery in three misses its promise, and in this data neither a late delivery nor a campaign channel moves the rating or ROAS, so the levers are assortment and delay recovery, not channel mix.
- **Genre:** curated, screenfit pages with action titles (DAX title measures), plus one analytic page with slicers.
- Currency is not stated in the data. Show amounts as ₹ (Blinkit is Indian) and say "currency assumed INR" in the footer.

## Three business questions
1. **Sales and category performance:** how much revenue, from which categories, products and payment methods, and how is it trending month on month?
2. **Delivery SLA vs customer experience:** how often do we hit the promised time, how late are the misses, and does lateness change rating or sentiment?
3. **Marketing return:** which channels, audiences and campaigns return the most revenue per rupee spent (ROAS, CTR, conversion), and is spend efficient?

## Headline KPI (links behaviour to revenue)
**Revenue at Risk** = revenue of orders that had a poor experience (delivered late, or rated 1-2 stars).

Decomposition (all on the orders table, grain = order):
`Revenue at Risk = Orders x Poor-experience rate x Avg order value of those orders`
- Orders = `COUNTROWS(orders)`; Poor-experience rate = orders with `delivery_status <> "On Time"` or `rating <= 2`, divided by Orders; AOV = `order_total` mean.
- Companion cards: Revenue, Orders, AOV, On-time rate, Avg rating, ROAS.
- Honest reading (from the audit): delay and rating are statistically independent here (corr 0.00), so the page shows both reasons separately and says the link is not supported by this data. Phase 2 will compute the exact figures (R1).

## Page plan (7 pages, screenfit, stratified layout: KPI row on top, detail below)
| # | Page (action title is a DAX measure) | Visuals and chart type (playbook section) |
|---|---|---|
| 1 | **Executive overview**: revenue, orders, AOV, on-time %, rating, revenue at risk | 6 KPI cards with change arrow plus sparkline; revenue by month line (even intervals, straight segments, March 2023 and November 2024 partial months flagged); category sorted bar (single hue, accent on top category); slicers date, category, payment. |
| 2 | **Sales and categories** (Q1) | Sorted horizontal bar of revenue by category (zero baseline); treemap only as secondary share view; top 10 products sorted bar; matrix heatmap category x month with a ColorBrewer sequential scheme; payment-method sorted bar (4 values, not a pie). |
| 3 | **Delivery performance** (Q2) | Stacked 100% bar of status by month is avoided (only bottom segment compares): use small-multiple lines of on-time %, slight and significant delay rate; histogram of minutes late (bins of 5 min, n shown); bar of delay by hour of day; card for "reason = Traffic only". |
| 4 | **Customer experience** (Q2) | Rating distribution column (1-5, uses Rating_Icon emoji); mean rating by delivery status as a dot/bar with n labels (shows the flat relationship, annotated); sentiment by feedback category matrix with diverging RdBu (variance from neutral); customer segment bars. |
| 5 | **Marketing ROI** (Q3) | Channel x audience matrix heatmap of ROAS (sequential); ROAS by channel sorted bar with spend labels; monthly spend vs revenue as two separate panels (no dual axis); funnel as three cards (impressions, clicks, conversions with rates); scatter spend vs revenue per campaign row with ROAS reference line, transparency for overplotting. |
| 6 | **Key insights and data notes** | Five action-title callouts, data lineage (source, refresh, "synthetic dataset" caveat, INR assumption, definitions of revenue and on-time). |
| 7 | **Forecast and levers** | 3-month revenue forecast (line with confidence band, Python output loaded as a table, fallback to DAX linear trend); lever table (what-if parameter: raise on-time rate or cut ROAS floor) with revenue-at-risk reduction; grey context, one accent. |

Interaction ideas
- **Drill-through** to a "Category detail" page (products, margin %, delivery rate, rating) from the category bar and to "Campaign detail" from the ROAS bar.
- **Tooltip pages:** category tooltip (monthly sparkline, top 3 products, damage rate), channel tooltip (CTR, conversion rate, spend).
- Page navigator, phone layouts for pages 1 and 6, bookmarks for "last 12 full months".
- Use `Category_Icons.xlsx` (category -> image URL) and `Rating_Icon.xlsx` (rating -> emoji URL, star text) as lookup dims; check image URLs render in Desktop and fall back to text.

Colour: brand palette for categories (<= 6 hues plus grey, direct labels), ColorBrewer sequential (Blues or YlGn, Blinkit-yellow accent for focus) for magnitudes, RdBu for variances; never red/green only.

## Star-schema sketch
| Table | Type | Grain | Keys / notes |
|---|---|---|---|
| `fact_orders` | fact | 1 row per order (5,000) | order_id PK; customer_id, store_id, delivery_partner_id, date_key; order_total, payment_method, status; joins delivery and feedback 1:1 (merge into this fact, or keep as 1:1 facts) |
| `fact_order_items` | fact | 1 row per order line (5,000, one product per order) | order_id, product_id; quantity, unit_price, line_amount = quantity x unit_price |
| `fact_delivery` | fact (1:1 with orders) | order | minutes_late (= `delivery_time_minutes`, can be negative = early), distance_km, reason, status |
| `fact_feedback` | fact (1:1 with orders) | order | rating, sentiment, feedback_category (drop `feedback_text`, 25 templates) |
| `fact_marketing` | fact | 1 row per campaign-day record (5,400) | date_key, channel, target_audience; no key to orders (separate star) |
| `fact_inventory` | fact (optional) | product x month from `inventoryNew` | stock_received, damaged_stock |
| `dim_date` | dim | day (2023-03-01 to 2024-11-30), marked as date table | one dim shared by orders, marketing, inventory (month key) |
| `dim_product` | dim | product (268) | category, brand, price, mrp, margin_percentage, shelf_life_days |
| `dim_category` | dim | category (11) | icon URL from Category_Icons |
| `dim_customer` | dim | customer (2,500) | area, pincode, registration_date, segment; **no name, email, phone, address** |
| `dim_rating` | dim | rating 1-5 | emoji, star text |
| `dim_payment`, `dim_channel` | small dims (optional) | | for sort orders and slicers |

Relationships: dim -> fact one-to-many, single direction; avoid snowflaking dim_category by flattening into dim_product unless the icon is needed. Drop `customers.total_orders` and `avg_order_value` (unreliable, see caveats) and recompute from orders.

## Data caveats (from the audit)
1. **Synthetic data:** flat distributions (hour, weekday, distance, impressions, ROAS), 25 feedback sentences, one item per order, delay and rating uncorrelated (0.00), distance and time uncorrelated (0.00). Say so on the report.
2. **`order_total` does not equal quantity x unit_price** (matches 1 of 5,000; correlation -0.01; orders total 11.0M vs item lines 4.97M). Decision needed: use `order_total` as the revenue measure (the order header) and keep item lines only for category and product mix, labelled "line value". Do not mix the two on one visual.
3. **Customers:** 2,500 rows (handoff said 5,030, wrong), only 2,172 place orders; `total_orders` and `avg_order_value` do not match the orders table (115 of 2,500 and 12 of 2,172); 2,556 orders precede the customer's registration date. Use order-derived measures only; registration date is not trustworthy for cohorts.
4. **Delivery:** `delivery_time_minutes` is minutes late versus promise (-5 to 30), not trip duration; "On Time" includes up to 5 minutes late (1,568 rows); statuses match between tables (5,000 of 5,000); the only delay reason is "Traffic" (also filled on 1,568 on-time rows), so reason analysis is empty.
5. **Marketing:** `roas` does not equal revenue_generated / spend (26 of 5,400 match); recompute ROAS in DAX as sum revenue / sum spend (portfolio 1.97 vs mean of stored roas 2.73). `campaign_id` is a row id; 9 campaign names. Marketing revenue (32.2M) is 2.9x total order revenue, so it cannot be joined or reconciled to orders; report it as a separate "attributed revenue".
6. **Inventory:** `inventory` (daily, 75,172 rows) has a 54% damage rate and damaged > received on 29,255 rows; `inventoryNew` (monthly Mon-YY, 18,105 rows, 1-6 rows per product-month, 3.9% damage) is the one to use, summed to product x month. No stock levels, no join to orders.
7. **Partial months:** March 2023 (120 orders) and November 2024 (30 orders, to 4 Nov) are partial; exclude from trend comparison and the forecast. Steady state is about 250 orders per month, so month-on-month change is noise.
8. **Store and partner ids:** every order has a unique store_id and partner id (5,000 distinct), so there is no store or rider analysis. Brands are almost one per product (267 brands for 268 products), so brand analysis is meaningless, and only 51 distinct product names cover 268 products (use product_id as the key; a product-name visual would merge products).
9. **Privacy:** `customer_name`, `email`, `phone`, `address` are dropped in the Python load step; they never appear in docs, the model or git.
