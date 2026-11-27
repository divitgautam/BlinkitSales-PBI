"""Loading helpers for the analysis notebooks. Personal fields never enter memory:
raw CSVs are read with a column filter that drops customer_name, email, phone and address; the clean tables never had them."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, CLEAN, DOCS = ROOT / "data/raw", ROOT / "data/clean", ROOT / "docs"
PII = {"customer_name", "email", "phone", "address"}
PARTIAL = [pd.Timestamp("2023-03-01"), pd.Timestamp("2024-11-01")]
LAST_FULL = pd.Timestamp("2024-10-01")


def raw(name, **kw):
    """Read data/raw/blinkit_<name>.csv without the personal columns."""
    return pd.read_csv(RAW / f"blinkit_{name}.csv", usecols=lambda c: c not in PII, **kw)


def clean(name):
    return pd.read_parquet(CLEAN / f"{name}.parquet")


def orders_enriched():
    """fact_orders + customer area/segment/registration + product category/price/mrp/margin, plus helper columns."""
    o, cu, pr = clean("fact_orders"), clean("dim_customer"), clean("dim_product")
    o = (o.merge(cu[["customer_id", "area", "segment", "registration_date"]], on="customer_id", how="left", validate="m:1")
          .merge(pr[["product_id", "category", "price", "mrp", "margin_percentage"]], on="product_id", how="left", validate="m:1", suffixes=("", "_p")))
    o["dow"] = o.order_date.dt.dayofweek
    o["dow_name"] = o.order_date.dt.day_name().str[:3]
    o["discount"] = 1 - o.price / o.mrp
    o["low_rating"] = o.rating <= 2
    o["experience"] = np.select([o.is_late & o.low_rating, o.is_late, o.low_rating], ["Both", "Late only", "Low rating only"], "Good")
    o["dist_band"] = pd.cut(o.distance_km, [0, 1.5, 2.5, 3.5, 5.0], labels=["0.5-1.5 km", "1.5-2.5 km", "2.5-3.5 km", "3.5-5 km"], include_lowest=True)
    o["day_part"] = pd.cut(o.order_hour, [-1, 5, 11, 16, 20, 23], labels=["Night 0-5", "Morning 6-11", "Afternoon 12-16", "Evening 17-20", "Late 21-23"])
    return o


def headline_numbers(o, mk, inv):
    """The numbers of docs/reconciliation.md, recomputed from the clean tables."""
    rev, n = o.order_total.sum(), len(o)
    cust = o.groupby("customer_id").size()
    poor = o.poor_experience
    ch = mk.groupby("channel")[["spend", "attributed_revenue"]].sum()
    return {
        "revenue": rev, "orders": n, "aov": rev / n, "customers_ordering": o.customer_id.nunique(),
        "repeat_rate": (cust >= 2).mean(), "on_time": 1 - o.is_late.mean(), "late": o.is_late.mean(),
        "avg_minutes_late": o.minutes_late.mean(), "avg_minutes_late_late_only": o.loc[o.is_late, "minutes_late"].mean(),
        "avg_rating": o.rating.mean(), "poor_rate": poor.mean(), "rar": o.loc[poor, "order_total"].sum(),
        "rar_share": o.loc[poor, "order_total"].sum() / rev,
        "roas": mk.attributed_revenue.sum() / mk.spend.sum(), "roas_channel": (ch.attributed_revenue / ch.spend).to_dict(),
        "damage_rate": inv.damaged_stock.sum() / inv.stock_received.sum(),
    }


def monthly_revenue(o, full_only=True):
    d = o[o.is_full_month] if full_only else o
    return d.groupby("month_start").order_total.sum()
