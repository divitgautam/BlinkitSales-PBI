"""Phase 2: raw CSVs -> star-schema tables in data/clean (CSV + parquet) and docs/data_dictionary.md.
Rerunnable and quiet; asserts on row counts and keys. Personal fields (name, email, phone, address) are dropped."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT, DOCS = ROOT / "data/raw", ROOT / "data/clean", ROOT / "docs"
OUT.mkdir(parents=True, exist_ok=True)
PARTIAL = [pd.Timestamp("2023-03-01"), pd.Timestamp("2024-11-01")]


def rd(name, **kw):
    return pd.read_csv(RAW / f"blinkit_{name}.csv", **kw)


def month_start(s):
    return s.dt.to_period("M").dt.to_timestamp()


# ---------- load
orders = rd("orders", parse_dates=["order_date"])
items = rd("order_items")
deliv = rd("delivery_performance")
fb = rd("customer_feedback")
prod = rd("products")
cust = rd("customers", usecols=["customer_id", "area", "pincode", "registration_date", "customer_segment"],
          parse_dates=["registration_date"])
mkt = rd("marketing_performance", parse_dates=["date"])
inv = rd("inventoryNew")

assert len(orders) == 5000 and orders.order_id.is_unique
assert len(items) == 5000 and items.order_id.is_unique
assert len(deliv) == 5000 and deliv.order_id.is_unique and len(fb) == 5000 and fb.order_id.is_unique
assert len(prod) == 268 and prod.product_id.is_unique and len(cust) == 2500 and cust.customer_id.is_unique
assert len(mkt) == 5400 and len(inv) == 18105

# ---------- fact_orders
items["line_value"] = (items.quantity * items.unit_price).round(2)
d = deliv[["order_id", "delivery_time_minutes", "distance_km", "reasons_if_delayed"]].rename(
    columns={"delivery_time_minutes": "minutes_late", "reasons_if_delayed": "delay_reason"})
f = fb[["order_id", "rating", "sentiment", "feedback_category"]]
fo = (orders.merge(items, on="order_id", validate="1:1")
      .merge(d, on="order_id", validate="1:1").merge(f, on="order_id", validate="1:1"))
assert len(fo) == 5000
fo = fo.rename(columns={"order_date": "order_datetime"})
fo["order_date"] = fo.order_datetime.dt.normalize()
fo["order_hour"] = fo.order_datetime.dt.hour
fo["month_start"] = month_start(fo.order_date)
fo["is_full_month"] = ~fo.month_start.isin(PARTIAL)
fo["minutes_late"] = fo.minutes_late.astype(int)
fo["is_late"] = (fo.delivery_status == "Significantly Delayed") | (fo.minutes_late > 5)
fo["poor_experience"] = fo.is_late | (fo.rating <= 2)
fo["rating"] = fo.rating.astype(int)
fo["delay_reason"] = fo.delay_reason.fillna("")
fo = fo[["order_id", "customer_id", "product_id", "order_date", "order_datetime", "order_hour", "month_start",
         "is_full_month", "order_total", "line_value", "quantity", "unit_price", "payment_method",
         "delivery_status", "minutes_late", "is_late", "distance_km", "delay_reason", "rating", "sentiment",
         "feedback_category", "poor_experience"]].sort_values("order_datetime", ignore_index=True)
assert fo.product_id.isin(prod.product_id).all() and fo.customer_id.isin(cust.customer_id).all()

# ---------- dim_customer (metrics derived from orders only)
g = fo.groupby("customer_id").agg(first_order_date=("order_date", "min"), orders=("order_id", "count"),
                                  revenue=("order_total", "sum"))
dc = cust.merge(g, on="customer_id", how="left")
dc["orders"] = dc.orders.fillna(0).astype(int)
dc["revenue"] = dc.revenue.fillna(0.0).round(2)
dc["customer_type"] = pd.Series("No orders", index=dc.index).mask(dc.orders == 1, "New").mask(dc.orders > 1, "Repeat")
dc = dc.rename(columns={"customer_segment": "segment"})
assert len(dc) == 2500 and (dc.orders > 0).sum() == 2172 and dc.orders.sum() == 5000

# ---------- dim_product
dp = prod.copy()
dp["product_label"] = dp.product_name + " (" + dp.product_id.astype(str) + ")"
dp = dp[["product_id", "product_name", "product_label", "category", "brand", "price", "mrp", "margin_percentage",
         "shelf_life_days", "min_stock_level", "max_stock_level"]]

# ---------- fact_marketing
fm = mkt.drop(columns=["roas"]).rename(columns={"revenue_generated": "attributed_revenue"})
fm["month_start"] = month_start(fm.date)
fm["is_full_month"] = ~fm.month_start.isin(PARTIAL)
fm["roas"] = (fm.attributed_revenue / fm.spend).round(4)
fm = fm[["campaign_id", "campaign_name", "date", "month_start", "is_full_month", "channel", "target_audience",
         "impressions", "clicks", "conversions", "spend", "attributed_revenue", "roas"]].sort_values(
    ["date", "campaign_id"], ignore_index=True)

# ---------- fact_inventory (product x month)
inv["month_start"] = pd.to_datetime(inv.date, format="%b-%y")
fi = inv.groupby(["product_id", "month_start"], as_index=False).agg(
    stock_received=("stock_received", "sum"), damaged_stock=("damaged_stock", "sum"))
fi["is_full_month"] = ~fi.month_start.isin(PARTIAL)
assert not fi.duplicated(["product_id", "month_start"]).any()
assert fi.stock_received.sum() == inv.stock_received.sum() and fi.product_id.isin(prod.product_id).all()

# ---------- write (CSV with ISO dates, parquet copies)
tables = {"fact_orders": fo, "fact_marketing": fm, "fact_inventory": fi, "dim_product": dp, "dim_customer": dc}
for name, t in tables.items():
    t.to_parquet(OUT / f"{name}.parquet", index=False)
    c = t.copy()
    if name == "fact_orders":
        c["order_datetime"] = c.order_datetime.dt.strftime("%Y-%m-%d %H:%M:%S")
    c.to_csv(OUT / f"{name}.csv", index=False, encoding="utf-8", date_format="%Y-%m-%d")

# ---------- data dictionary
DICT = {
 "fact_orders": ("One row per order (5,000). Orders, one item line, delivery and feedback merged 1:1. Source: orders, order_items, delivery_performance, customer_feedback.", [
  ("order_id", "Order key (unique)."), ("customer_id", "FK to dim_customer."), ("product_id", "FK to dim_product (one item per order)."),
  ("order_date", "Order date (day)."), ("order_datetime", "Order timestamp, ISO."), ("order_hour", "Hour of day 0-23."),
  ("month_start", "First day of the order month (join to a Date table)."),
  ("is_full_month", "False for the partial months Mar 2023 and Nov 2024; exclude from trends and YoY."),
  ("order_total", "Order header total in assumed INR. THE revenue measure (revenue, AOV, Revenue at Risk)."),
  ("line_value", "quantity x unit_price. Only for category/product mix; does not reconcile to order_total (total 4.97M vs 11.01M)."),
  ("quantity", "Units on the item line (1-3)."), ("unit_price", "Item unit price."), ("payment_method", "Card, Cash, UPI or Wallet."),
  ("delivery_status", "On Time, Slightly Delayed or Significantly Delayed."),
  ("minutes_late", "Actual minus promised delivery time, minutes (-5 to 30; negative = early)."),
  ("is_late", "Significantly Delayed or minutes_late > 5 (equals status not On Time)."),
  ("distance_km", "Delivery distance."), ("delay_reason", "Stored reason; only 'Traffic' or blank (also set on some on-time rows, do not analyse)."),
  ("rating", "Customer rating 1-5."), ("sentiment", "Positive, Neutral or Negative."), ("feedback_category", "Delivery, Customer Service, Product Quality or App Experience."),
  ("poor_experience", "is_late OR rating <= 2. Basis of Revenue at Risk.")]),
 "fact_marketing": ("One row per campaign record (5,400). No key to orders.", [
  ("campaign_id", "Row id (not a campaign key)."), ("campaign_name", "9 campaign names."), ("date", "Record date."),
  ("month_start", "First day of month."), ("channel", "App, Email, SMS or Social Media."),
  ("target_audience", "All, Inactive, New Users or Premium."), ("impressions", "Impressions."), ("clicks", "Clicks."), ("conversions", "Conversions."),
  ("spend", "Campaign spend, assumed INR."), ("attributed_revenue", "Source revenue_generated; attributed, not order revenue (2.9x orders total)."),
  ("roas", "Recomputed attributed_revenue / spend (stored roas dropped: it did not match). Aggregate in DAX as SUM/SUM.")]),
 "fact_inventory": ("Product x month (inventoryNew summed; daily 'inventory' file dropped, 54% damage rate).", [
  ("product_id", "FK to dim_product."), ("month_start", "First day of month (source 'Mon-YY')."), ("stock_received", "Units received, summed."),
  ("damaged_stock", "Units damaged, summed."), ("is_full_month", "False for Mar 2023 and Nov 2024.")]),
 "dim_product": ("One row per product (268).", [
  ("product_id", "Key."), ("product_name", "Name (only 51 distinct; not unique)."), ("product_label", "Name plus id, unique; use in visuals."),
  ("category", "11 categories."), ("brand", "Brand (about one per product; not useful)."), ("price", "List price."), ("mrp", "Maximum retail price."),
  ("margin_percentage", "Stored margin %, 15-40."), ("shelf_life_days", "Shelf life."), ("min_stock_level", "Min stock level."), ("max_stock_level", "Max stock level.")]),
 "dim_customer": ("One row per customer in customers.csv (2,500; 2,172 have orders). Name, email, phone, address removed. Metrics derived from orders, not from customers.csv.", [
  ("customer_id", "Key."), ("area", "Area."), ("pincode", "Pincode."), ("registration_date", "Stored registration date (unreliable: 2,556 orders precede it)."),
  ("segment", "Stored segment: Regular, Premium, New, Inactive."), ("first_order_date", "Earliest order date; blank if no orders."),
  ("orders", "Order count from fact_orders."), ("revenue", "Sum of order_total from fact_orders."),
  ("customer_type", "New = 1 order, Repeat = 2+ orders, No orders = 0.")]),
}
FULL_MONTH_COLS = ("is_full_month", "False for Mar 2023 and Nov 2024; exclude from trends and YoY.")
DICT["fact_marketing"][1].insert(4, FULL_MONTH_COLS)
L = ["# Data dictionary (generated by `_build/prepare.py`)\n",
     "Clean tables in `data/clean/` (CSV UTF-8, ISO dates; parquet copies). Currency is not stated in the source; shown as INR. "
     "Dropped everywhere: customer_name, email, phone, address, store_id, delivery_partner_id (5,000 unique ids), feedback_text, "
     "stored customer total_orders / avg_order_value, stored roas, daily inventory file.\n"]
for n, (desc, cols) in DICT.items():
    t = tables[n]
    assert [c for c, _ in cols] == list(t.columns), n
    L += [f"## {n}\n", f"{desc} Rows: {len(t):,}.\n", "| column | type | description |", "|---|---|---|"]
    L += [f"| {c} | {t[c].dtype} | {x} |" for c, x in cols] + [""]
(DOCS / "data_dictionary.md").write_text("\n".join(L), encoding="utf-8")
print("prepare OK:", {n: len(t) for n, t in tables.items()})
