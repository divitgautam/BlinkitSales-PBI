# %% [markdown]
# # 03 · Forecast and backtest
# Re-creates the rolling-origin backtest of `_build/forecast.py` (train on 10 to 13 full months, forecast the next 6) so the chart
# and the published model agree, then draws the forecast with its 80% band from `data/clean/forecast.csv`. No new modelling: the report's forecast is reused.
# %%
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from IPython.display import display
from viz_style import *
from data_io import *
o = clean("fact_orders")
m = monthly_revenue(o)
y = m.values
assert len(y) == 19 and m.index[0] == pd.Timestamp("2023-04-01") and m.index[-1] == LAST_FULL
FC = pd.read_csv(CLEAN / "forecast.csv", parse_dates=["month_start"])
FACTS = json.loads((CLEAN / "report_facts.json").read_text(encoding="utf-8"))
H = 6
MODELS = {
    "Naive (last full month)": lambda h, n: np.repeat(h[-1], n),
    "Mean of last 3 months": lambda h, n: np.repeat(h[-3:].mean(), n),
    "Mean of last 6 months": lambda h, n: np.repeat(h[-6:].mean(), n),
    "Mean of all months": lambda h, n: np.repeat(h.mean(), n),
    "Linear trend": lambda h, n: np.polyval(np.polyfit(np.arange(len(h)), h, 1), np.arange(len(h), len(h) + n)),
    "Seasonal naive (same month last year)": lambda h, n: h[len(h) - 12:len(h) - 12 + n] if len(h) >= 12 else np.repeat(np.nan, n),
}
def backtest(fn):
    e = []
    for i in range(10, len(y) - H + 1):
        e += list(np.abs(y[i:i + H] - fn(y[:i], H)) / y[i:i + H])
    return np.array(e)
bt = pd.DataFrame([(k, np.nanmean(backtest(f)) * 100) for k, f in MODELS.items()], columns=["model", "mape"]).sort_values("mape").reset_index(drop=True)
display(bt.round(2))
assert round(bt.mape.iloc[0], 2) == FACTS["backtest_mape"] == 2.77 and bt.model.iloc[0] == FACTS["backtest_best"]
errs = backtest(MODELS[bt.model.iloc[0]]); q80 = np.quantile(errs, .8)
assert abs(q80 - FACTS["band80"]) < 5e-4
point = float(FC.forecast.dropna().iloc[-1]); assert abs(point - FACTS["f_month"]) < 1
f25 = FC[(FC.kind == "Forecast") & (FC.month_start.dt.year == 2025)].forecast.sum()
assert abs(f25 - FACTS["f25"]) < 1
print("best model", bt.model.iloc[0], "| MAPE", round(bt.mape.iloc[0], 2), "| 80% band", f"+/-{q80:.1%}", "| forecast / month", round(point), "| 2025", round(f25), "| LTM", round(y[-12:].sum()))
# %% [markdown]
# ## 1. Backtest: the simplest model wins, and every model is within a few percent of the actual
# %%
hold_n = H
tr, te = y[:-hold_n], y[-hold_n:]
pred = MODELS[bt.model.iloc[0]](tr, hold_n)
mape_hold = np.mean(np.abs(te - pred) / te) * 100
fig, (a1, a2) = new_fig(h=4.8, ncols=2, gridspec_kw={"width_ratios": [1, 1.25]}, left=0.2)
bar_h(a1, [k.replace(" (same month last year)", "\n(same month last year)") for k in bt.model], bt.mape.values, fmt=lambda v: f"{v:.2f}%", highlight=[0])
a1.set_title("Backtest error (MAPE), rolling origin, 6-month horizon")
idx = m.index
a2.plot(idx[:-hold_n], tr / 1e5, color=GREY, marker="o", ms=3.5, lw=1.5, label="training months")
a2.plot(idx[-hold_n:], te / 1e5, color=GREEN, marker="o", ms=4.5, lw=2, label="actual (held out)")
a2.hlines(pred[0] / 1e5, idx[-hold_n], idx[-1], color=INK, lw=1.8, ls="--", label=f"naive forecast, MAPE {mape_hold:.2f}%")
a2.fill_between(idx[-hold_n:], pred[0] * (1 - q80) / 1e5, pred[0] * (1 + q80) / 1e5, color=YELLOW, alpha=.45, lw=0, label=f"80% band (+/-{q80:.1%})")
a2.set_ylim(0, 8); a2.set_ylabel("Revenue, ₹ lakh"); clean_axes(a2); a2.legend(loc="lower left", ncol=2, fontsize=8); a2.set_title("Hold-out: train to Apr 2024, forecast May to Oct 2024"); month_axis(a2)
headline(fig, f"The naive 'same as last month' forecast wins the backtest at {bt.mape.iloc[0]:.2f}% error; trend and seasonal models are worse",
         "Left: mean absolute percentage error of six candidate models. Right: the winning model on the last six months")
footnote(fig, "Source: data/clean fact_orders, 19 full months (Apr 2023 to Oct 2024); same method as _build/forecast.py. With 19 noisy points a seasonal pattern cannot be estimated.")
print(save(fig, "ds/forecast_backtest"))
# %% [markdown]
# ## 2. Forecast with the 80% band
# %%
act = FC[FC.kind == "Actual"]; fut = FC[FC.kind == "Forecast"]
ltm = y[-12:].sum()
fig, ax = new_fig(h=4.8)
ax.plot(act.month_start, act.actual / 1e5, color=GREEN, marker="o", ms=4, lw=2, label="actual (full months)")
ax.plot(fut.month_start, fut.forecast / 1e5, color=INK, ls="--", lw=1.8, label="forecast: ₹5.38 L a month")
ax.fill_between(fut.month_start, fut.low80 / 1e5, fut.high80 / 1e5, color=YELLOW, alpha=.5, lw=0, label="80% band (+/-5%)")
ax.axvline(pd.Timestamp("2024-10-16"), color=LTGREY, lw=1)
ax.set_ylim(0, 8); ax.set_ylabel("Revenue, ₹ lakh"); clean_axes(ax); ax.legend(loc="lower left", ncol=3); month_axis(ax)
lo25, hi25 = fut[fut.month_start.dt.year == 2025].low80.sum(), fut[fut.month_start.dt.year == 2025].high80.sum()
note(ax, .985, .93, f"2025 total ₹{f25 / 1e5:.2f} L (80% band {lo25 / 1e5:.1f} to {hi25 / 1e5:.1f} L)\nlast 12 full months ₹{ltm / 1e5:.2f} L; 2025 is {f25 / ltm - 1:+.1%}", transform=ax.transAxes, ha="right", va="top", fontsize=9.5)
headline(fig, f"Expect about ₹5.4 L a month in 2025, a flat line within +/-5%; 2025 totals ₹{f25 / 1e5:.1f} L, {abs(f25 / ltm - 1):.0%} below the last 12 months",
         "Monthly revenue: 19 full months of actuals and a 14-month forecast (Nov 2024 to Dec 2025)")
footnote(fig, "Source: data/clean/forecast.csv (_build/forecast.py). The band is the 80th percentile of the absolute backtest error, so it reflects month-to-month noise only; it is not a promise.")
print(save(fig, "ds/forecast_band"))
