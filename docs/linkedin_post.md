# LinkedIn post: BlinkitSales-PBI

**Attach, in this order:**
1. `docs/key_insights.png` (portrait)
2. `docs/approach.png`
3. `docs/dashboard/01_overview.png`
4. `docs/dashboard/03_delivery.png`
5. `docs/dashboard/07_forecast.png`

Repo: https://github.com/divitgautam/BlinkitSales-PBI (create it first, then check the link works). About 2,100 characters, under LinkedIn's 3,000 limit.

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

A naive forecast beat five other models in a rolling backtest (error 2.8%): about ₹64.5 L for 2025. Cutting late deliveries by 5 points would take ₹2.64 L of revenue out of the at-risk group.

How it was made: Python for the audit and for 70 reconciled numbers, then the model (186 measures) and the report generated from code. A layout checker, the Best Practice Analyzer (27 of 27) and a 10-point scorecard ran after every export. It took six rounds to get from 5.0 to 9.75, and one round was lost to a text box that overflowed by a few pixels.

Code, notes and a step-by-step guide: https://github.com/divitgautam/BlinkitSales-PBI

What would you check first in a dataset like this?

#PowerBI #DataAnalytics #DAX #Python
