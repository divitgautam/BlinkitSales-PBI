"""Phase 4: honest monthly revenue forecast, lever sizing and report facts.
Run: python _build/forecast.py     (after prepare.py)
Writes data/clean/forecast.csv, data/clean/levers.csv, data/clean/report_facts.json, docs/forecast_levers.md.

Forecast: monthly Revenue (= SUM order_total) on FULL months only (Apr 2023 to Oct 2024, 19 points).
Candidate models are scored with a rolling-origin backtest (train on the first 10..13 months, forecast the next 6, repeat);
the model with the lowest MAPE is used, refitted on all 19 months. The 80% band is the 80th percentile of the absolute relative
backtest error. With 19 noisy points a seasonal pattern cannot be estimated: seasonal naive is in the table to show that."""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
CLEAN, DOCS = ROOT / "data" / "clean", ROOT / "docs"
H = 6                       # backtest horizon (months)
FIRST_FC, LAST_FC = pd.Timestamp("2024-11-01"), pd.Timestamp("2025-12-01")

fo = pd.read_csv(CLEAN / "fact_orders.csv", parse_dates=["order_date", "month_start"])
fm = pd.read_csv(CLEAN / "fact_marketing.csv", parse_dates=["date", "month_start"])
fi = pd.read_csv(CLEAN / "fact_inventory.csv", parse_dates=["month_start"])
dp = pd.read_csv(CLEAN / "dim_product.csv")

# ------------------------------------------------------------------ forecast
m = fo[fo.is_full_month].groupby("month_start").order_total.sum().sort_index()
y, idx = m.values, m.index
assert len(y) == 19 and idx[0] == pd.Timestamp("2023-04-01") and idx[-1] == pd.Timestamp("2024-10-01")

MODELS = {
    "Naive (last full month)": lambda h, n: np.repeat(h[-1], n),
    "Mean of last 3 months": lambda h, n: np.repeat(h[-3:].mean(), n),
    "Mean of last 6 months": lambda h, n: np.repeat(h[-6:].mean(), n),
    "Mean of all months": lambda h, n: np.repeat(h.mean(), n),
    "Linear trend": lambda h, n: np.polyval(np.polyfit(np.arange(len(h)), h, 1), np.arange(len(h), len(h) + n)),
    "Seasonal naive (same month last year)": lambda h, n: h[len(h) - 12:len(h) - 12 + n] if len(h) >= 12 else np.repeat(np.nan, n),
}


def backtest(fn):
    errs = []
    for i in range(10, len(y) - H + 1):
        p = fn(y[:i], H)
        errs += list(np.abs(y[i:i + H] - p) / y[i:i + H])
    return np.array(errs)


rows = []
for name, fn in MODELS.items():
    e = backtest(fn)
    rows.append((name, np.nanmean(e) * 100, int(np.isfinite(e).sum())))
bt = pd.DataFrame(rows, columns=["model", "mape", "n"]).sort_values("mape")
best = bt.iloc[0].model
errs = backtest(MODELS[best])
mape = errs.mean() * 100
q80 = np.quantile(errs, 0.80)
# holdout view: train Apr 2023 to Apr 2024 (13 months), forecast May to Oct 2024
hold = np.abs(y[-H:] - MODELS[best](y[:-H], H)) / y[-H:]
mape_hold = hold.mean() * 100

future = pd.date_range(FIRST_FC, LAST_FC, freq="MS")
point = MODELS[best](y, len(future))
low, high = point * (1 - q80), point * (1 + q80)
fc = pd.concat([
    pd.DataFrame({"month_start": idx, "kind": "Actual", "actual": y, "forecast": np.nan, "low80": np.nan, "high80": np.nan}),
    pd.DataFrame({"month_start": future, "kind": "Forecast", "actual": np.nan, "forecast": point, "low80": low, "high80": high})])
fc.loc[fc.index[len(y) - 1], ["forecast", "low80", "high80"]] = y[-1]      # first row: join the lines at the last actual month
fc = pd.concat([fc.iloc[:len(y)], fc.iloc[len(y):]]).reset_index(drop=True)
fc["month_start"] = fc.month_start.dt.strftime("%Y-%m-%d")
fc.round(2).to_csv(CLEAN / "forecast.csv", index=False)
f25 = point[future.year == 2025].sum()
f25_lo, f25_hi = low[future.year == 2025].sum(), high[future.year == 2025].sum()
ltm = y[-12:].sum()                                      # last twelve full months, Nov 2023 to Oct 2024
fc_month = float(point[0])

# ------------------------------------------------------------------ levers (basis: last 12 full months, Nov 2023 to Oct 2024)
LTM = (fo.month_start >= "2023-11-01") & (fo.month_start <= "2024-10-01")
o12 = fo[LTM]
rev12, n12 = o12.order_total.sum(), len(o12)
late_rate = o12.is_late.mean()
low_rate = (o12.rating <= 2).mean()
levers = []

# 1 late deliveries: remove a fraction of late orders; only orders that are not also low-rated leave the at-risk pool
LATE_CUT = 0.05
frac = LATE_CUT / late_rate
exp1 = frac * o12.loc[o12.is_late & (o12.rating > 2), "order_total"].sum()
levers.append(("Cut late deliveries by 5 points", "Exposure removed", f"Late share {late_rate:.1%} to {late_rate - LATE_CUT:.1%}; "
               "late orders that are also rated 1-2 stars stay at risk", exp1, "Low: delay does not move the rating in this data"))
# 2 low ratings
LOW_CUT = 0.05
frac2 = LOW_CUT / low_rate
exp2 = frac2 * o12.loc[(o12.rating <= 2) & ~o12.is_late, "order_total"].sum()
levers.append(("Cut 1-2 star ratings by 5 points", "Exposure removed", f"Low-rating share {low_rate:.1%} to {low_rate - LOW_CUT:.1%}; "
               "low-rated orders that are also late stay at risk", exp2, "Low: no cause identified in the data"))
# 3 marketing: move 20% of the lowest-ROAS channel's spend to the highest (full-period ROAS, last-12-month spend)
ch = fm.groupby("channel")[["spend", "attributed_revenue"]].sum()
ch["roas"] = ch.attributed_revenue / ch.spend
hi_ch, lo_ch = ch.roas.idxmax(), ch.roas.idxmin()
sp12 = fm[(fm.month_start >= "2023-11-01") & (fm.month_start <= "2024-10-01")].groupby("channel").spend.sum()
SHIFT = 0.20
gain3 = SHIFT * sp12[lo_ch] * (ch.roas[hi_ch] - ch.roas[lo_ch])
rng = np.random.default_rng(42)
diffs = []
ge, gl = fm[fm.channel == hi_ch], fm[fm.channel == lo_ch]
for _ in range(2000):
    a, b = ge.sample(len(ge), replace=True, random_state=int(rng.integers(1e9))), gl.sample(len(gl), replace=True, random_state=int(rng.integers(1e9)))
    diffs.append(a.attributed_revenue.sum() / a.spend.sum() - b.attributed_revenue.sum() / b.spend.sum())
d_lo, d_hi = np.quantile(diffs, [0.025, 0.975])
levers.append((f"Move 20% of {lo_ch} spend to {hi_ch}", "Attributed revenue gained",
               f"{lo_ch} ROAS {ch.roas[lo_ch]:.2f}x vs {hi_ch} {ch.roas[hi_ch]:.2f}x; bootstrap 95% interval of the gap {d_lo:+.2f} to {d_hi:+.2f}x",
               gain3, "Low: small gap, and attributed revenue is not order revenue"))
# 4 damage: units saved x list price
inv12 = fi[(fi.month_start >= "2023-11-01") & (fi.month_start <= "2024-10-01")].merge(dp[["product_id", "price"]], on="product_id")
dmg_rate = inv12.damaged_stock.sum() / inv12.stock_received.sum()
DMG_CUT = 0.005
price_w = (inv12.stock_received * inv12.price).sum() / inv12.stock_received.sum()
gain4 = DMG_CUT * inv12.stock_received.sum() * price_w
levers.append(("Cut stock damage by 0.5 points", "Stock value saved", f"Damage rate {dmg_rate:.2%} to {dmg_rate - DMG_CUT:.2%} of units received, valued at list price "
               "(upper bound: cost price is lower)", gain4, "Medium: unit counts are real, value is at list price"))
lv = pd.DataFrame(levers, columns=["lever", "lever_type", "assumption", "annual_value", "confidence"])
lv["pct_of_revenue"] = lv.annual_value / rev12
lv["lever_label"] = [f"{short} ({tag})" for short, tag in zip(
    lv.lever.str.replace("points", "pts").str.replace("Move", "Shift"),
    lv.lever_type.map({"Exposure removed": "exposure", "Attributed revenue gained": "attributed revenue", "Stock value saved": "stock value"}))]
lv["basis"] = "Nov 2023 to Oct 2024 (last 12 full months)"
lv = lv.sort_values("annual_value", ascending=False).reset_index(drop=True)
lv.round({"annual_value": 2, "pct_of_revenue": 6}).to_csv(CLEAN / "levers.csv", index=False)

# ------------------------------------------------------------------ report facts for the insight page
inr = lambda v: (f"₹{v / 1e7:.2f} Cr" if abs(v) >= 1e7 else f"₹{v / 1e5:.2f} L" if abs(v) >= 1e5 else f"₹{v:,.0f}")
cat = fo.merge(dp[["product_id", "category"]], on="product_id").groupby("category").line_value.sum().sort_values(ascending=False)
poor = fo.poor_experience
facts = {
    "backtest_best": best, "backtest_mape": round(mape, 2), "holdout_mape": round(mape_hold, 2), "band80": round(q80, 4),
    "table": {r.model: round(r.mape, 2) for r in bt.itertuples()},
    "f_month": round(fc_month, 2), "f25": round(f25, 2), "f25_lo": round(f25_lo, 2), "f25_hi": round(f25_hi, 2), "ltm_revenue": round(ltm, 2),
    "f25_vs_ltm": round(f25 / ltm - 1, 4), "levers": {r.lever: round(r.annual_value, 2) for r in lv.itertuples()},
    "yoy_aprOct": round(fo[fo.is_full_month & (fo.month_start.dt.year == 2024) & (fo.month_start.dt.month >= 4)].order_total.sum()
                        / fo[fo.is_full_month & (fo.month_start.dt.year == 2023) & (fo.month_start.dt.month >= 4) & (fo.month_start.dt.month <= 10)].order_total.sum() - 1, 4),
    "top_cat": cat.index[0], "top_cat_share": round(cat.iloc[0] / cat.sum(), 4), "bottom_cat": cat.index[-1], "bottom_cat_share": round(cat.iloc[-1] / cat.sum(), 4),
    "top3_share": round(cat.iloc[:3].sum() / cat.sum(), 4),
    "late_only_share": round((fo.is_late & (fo.rating > 2)).sum() / poor.sum(), 4), "low_only_share": round((~fo.is_late & (fo.rating <= 2)).sum() / poor.sum(), 4),
    "both_share": round((fo.is_late & (fo.rating <= 2)).sum() / poor.sum(), 4),
    "corr_late_rating": round(float(np.corrcoef(fo.is_late.astype(float), fo.rating)[0, 1]), 3),
    "roas_gap_ci": [round(float(d_lo), 3), round(float(d_hi), 3)],
    "hi_channel": hi_ch, "lo_channel": lo_ch,
    "avg_orders_month": round(float(fo[fo.is_full_month].groupby("month_start").size().mean()), 1),
    "dmg_rate": round(dmg_rate, 4),
    "rating_late": round(float(fo.loc[fo.is_late, "rating"].mean()), 2), "rating_ontime": round(float(fo.loc[~fo.is_late, "rating"].mean()), 2),
    "low_rating_rate": round(float((fo.rating <= 2).mean()), 4), "mkt_to_order_rev": round(float(fm.attributed_revenue.sum() / fo.order_total.sum()), 2),
}
(CLEAN / "report_facts.json").write_text(json.dumps(facts, indent=2, ensure_ascii=False), encoding="utf-8")

# ------------------------------------------------------------------ method note
md = ["# Forecast and levers (generated by `_build/forecast.py`)\n",
      f"**Method.** Monthly revenue (SUM order_total) on the 19 full months Apr 2023 to Oct 2024. Rolling-origin backtest: train on the first 10 to 13 months, "
      f"forecast the next {H}, repeat. Best model by MAPE: **{best}** (MAPE {mape:.1f}%, {int(np.isfinite(errs).sum())} forecasts; "
      f"6-month holdout May to Oct 2024 trained on Apr 2023 to Apr 2024: {mape_hold:.1f}%). 80% band = ±{q80:.1%} (80th percentile of absolute backtest error).\n",
      "| Model | Backtest MAPE |", "|---|---|"] + [f"| {r.model} | {r.mape:.1f}% |" for r in bt.itertuples()] + [
      "",
      f"**Forecast.** Nov 2024 to Dec 2025: flat at {inr(fc_month)} a month (band {inr(low[0])} to {inr(high[0])}). 2025 total {inr(f25)} "
      f"(80% band {inr(f25_lo)} to {inr(f25_hi)}), {f25 / ltm - 1:+.1%} vs the last 12 full months ({inr(ltm)}). "
      f"Seasonality cannot be estimated from 19 noisy points (seasonal naive is the worst model); Apr to Oct 2024 ran {facts['yoy_aprOct']:+.1%} vs 2023, "
      "so the flat forecast already sits below last year. The data is synthetic: treat the forecast as a baseline, not a prediction.\n",
      "## Levers (basis: last 12 full months, Nov 2023 to Oct 2024; revenue " + inr(rev12) + ")\n",
      "| Lever | Type | Annual value | % of revenue | Assumption | Confidence |", "|---|---|---|---|---|---|"] + [
      f"| {r.lever} | {r.lever_type} | {inr(r.annual_value)} | {r.pct_of_revenue:.2%} | {r.assumption} | {r.confidence} |" for r in lv.itertuples()] + [
      "", "Lever values are not additive across types: exposure removed is revenue that stops being at risk, not new revenue; attributed revenue is the marketing "
      "file's own attribution; stock value is at list price."]
(DOCS / "forecast_levers.md").write_text("\n".join(md), encoding="utf-8")
print(bt.round(2).to_string(index=False))
print(f"best={best} backtest MAPE={mape:.2f}% holdout={mape_hold:.2f}% band=±{q80:.1%}")
print(f"forecast/month={inr(fc_month)} f2025={inr(f25)} ({inr(f25_lo)}..{inr(f25_hi)}) vs LTM {inr(ltm)} {f25 / ltm - 1:+.1%}")
for r in lv.itertuples():
    print(f"  {r.lever}: {inr(r.annual_value)} ({r.pct_of_revenue:.2%}) [{r.lever_type}]")
