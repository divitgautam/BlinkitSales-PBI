# LinkedIn post: BlinkitSales-PBI

**Attach, in this order:**
1. `docs/key_insights.png` (portrait)
2. `docs/approach.png`
3. `docs/dashboard/01_overview.png`
4. `docs/dashboard/03_delivery.png`
5. `docs/ds/rca_lateness_drivers.png` (root cause: no driver explains lateness)
6. `docs/ds/reorder_after_poor_experience.png` (the key question: does a bad order cost the next one?)
7. `docs/ds/rca_revenue_bridge.png` (revenue change split into volume, mix and basket value)
8. `docs/ds/cohort_retention.png` (flat 9% retention in every cohort)
9. `docs/dashboard/07_forecast.png`

Upload as one multi-image post (or a PDF carousel). If you want fewer images, keep 1, 3, 5, 6 and 7.

Repo: https://github.com/divitgautam/BlinkitSales-PBI (live). About 2,800 characters, under LinkedIn's 3,000 limit; check the count before posting.

---

## Post text (copy from here)

I built a seven-page Power BI report on a public Blinkit sales dataset, and the most useful thing I found was where the data does not agree with itself.

The brief had three questions: how are sales and categories doing, how does delivery speed relate to customer experience, and does marketing pay back.

Before any chart, I audited the files. Three things changed the design:
- Order totals match quantity x unit price on 1 of 5,000 orders (₹1.10 Cr against ₹49.7 L). So revenue uses the order total, and categories are labelled "line value".
- The stored ROAS column is wrong, so I recomputed it as revenue / spend.
- Marketing revenue is 2.9x total order revenue and has no key to orders, so it stays a separate view.

I also have to say it plainly: the data looks synthetic. Flat distributions, 25 feedback sentences, one item per order. The figures are illustrative, and the report says so on page 6.

What it shows:
- Sales are flat: about 255 orders a month, ₹1.10 Cr in total.
- 31% of orders miss the promised time, by 14.5 minutes on average.
- Late orders rate 3.37 stars, on-time orders 3.33. Delay does not move the rating here, yet ₹50.42 L (46% of revenue) sits in orders that were late or rated 1-2 stars.
- Categories are evenly spread: Dairy & Breakfast leads with 12.9%.
- Every channel returns 1.9x to 2.05x per rupee spent. Channel mix is not the lever.

A naive forecast beat five other models in a rolling backtest (error 2.8%): about ₹64.5 L for 2025.

Then I looked at it as a data scientist and tested whether any of this actually costs money. On this data, nothing I could measure:
- A poor experience shows no clear effect on the next order: 60-day reorder is 16.9% after one and 18.4% after a good one (odds ratio 0.90, CI 0.77 to 1.05). That is not proof of no effect; the interval still allows a real drop.
- Distance, hour, area and category explain none of the lateness. About 30% of orders are late everywhere.
- Marketing revenue does not move with spend (elasticity -0.01). ROAS only falls because spend rises.

So "₹50.42 L at risk" is revenue exposed to poor experiences, not revenue that will be lost. The next step is a test, not a fix: a marketing holdout needs about 239 units per arm to detect a 10% revenue effect.

How it was made: an audit and 70 reconciled numbers in Python, then the model (186 measures) and report generated from code, checked after every export until the scorecard went from 5.0 to 9.75. Behind it sit six notebooks and 29 charts: root cause of lateness, cohorts, RFM and a revenue bridge. A dashboard shows what happened; the analysis shows what is worth testing.

Code, the statistical review and a step-by-step guide: https://github.com/divitgautam/BlinkitSales-PBI

What would you check first in a dataset like this?

#PowerBI #DataAnalytics #DAX #Python
