import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from utils import *
from p3.p3 import Trader, PARAMETERS
import scipy
from trash.plot_lib import plot_book

# Grab States

use_cache = True
days = [4]
bt_states = get_trading_states_from_data("data_p3/all", days, use_p3=True, use_cache=use_cache)
bt_results = [Reaction(s, "", {}, {}, {}) for s in bt_states]
states = bt_states
timestamps = np.array([s.timestamp for s in states])
S = np.array([get_wall_mid(s.order_depths.get("VOLCANIC_ROCK", OrderDepth())) for s in states])
days_left = 7-min(days)
print(timestamps[-5:])
TTE = (days_left - timestamps / 10000_00)
def _norm_cdf(x):
    return 0.5 * (1.0 + scipy.special.erf(x / np.sqrt(2.0)))
def bs_price(S, K, T, r, sigma):
    sqrt_T = np.sqrt(T)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return S * _norm_cdf(d1) - K * np.exp(-r * T) * _norm_cdf(d2)
@np.vectorize
def implied_vol(V, S, K, TTE, r=0.0, tol=1e-6):
    return scipy.optimize.brentq(lambda sigma: bs_price(S, K, TTE, r, sigma) - V, 1e-6, 10.0, xtol=tol)
Ks = [9500, 9750, 10000, 10250, 10500]
m = {}
V = {}
sigma = {}
for K in tqdm(Ks):
    m[K] = np.log(K / S) / np.sqrt(TTE)
    V[K] = np.array([get_wall_mid(s.order_depths.get(f"VOLCANIC_ROCK_VOUCHER_{K}", OrderDepth())) for s in states])
    sigma[K] = implied_vol(V[K], S, K, TTE)
ms = np.array([mi for K in Ks for mi in m[K]])
sigmas = np.array([mi for K in Ks for mi in sigma[K]])
xy = np.array(sorted([[mi, sigmai] for mi, sigmai in zip(ms, sigmas) if sigmai > 0.005]))
a, b, c = np.polyfit(xy[:,0], xy[:,1], 2)
sigma_baselines = a*ms**2+b*ms+c
price_deviation = {K: V[K]-bs_price(S, K, TTE, 0, a*m[K]**2+b*m[K]+c) for K in Ks} # you get an implied volatility for the options and you see their behavior rel log(K/S)/sqrt(TTE). so you can predict option price with just sort of time and strike. this thing is deviation of current price from predicted theoretical price
print(a, b, c)
fig = make_subplots(rows=2+len(Ks), cols=1, shared_xaxes=False, vertical_spacing=0.01, specs=[[{"secondary_y": False}], [{"secondary_y": True}]] + [[{"secondary_y": True}]] * len(Ks))
K_colors = ["blue", "red", "green", "purple", "orange"]
for i in range(len(Ks)):
    fig.add_trace(go.Scatter(x=m[Ks[i]], y=sigma[Ks[i]], mode="markers", marker=dict(symbol="circle", color=K_colors[i], size=8), name=f"impl_vol_{Ks[i]}", customdata=[[t] for t in timestamps],hovertemplate="time: %{customdata[0]}<br>implied vol: %{y}"), row=1, col=1)
fig.add_trace(go.Scatter(x=xy[:,0], y=a*xy[:,0]**2+b*xy[:,0]+c, mode="lines", line=dict(color="black", width=3), name="smile fit"))
fig.add_trace(go.Scatter(x=timestamps, y=S, mode="lines", name="S"), row=2, col=1)
for i in range(len(Ks)):
    fig.add_hline(y=Ks[i], line_color=K_colors[i], line_width=1, row=2, col=1) # type: ignore # plotly api problem
    fig.add_trace(go.Scatter(x=timestamps, y=V[Ks[i]]-np.maximum(0, S-Ks[i]), mode="lines", line=dict(color=K_colors[i]), name=f"V_{Ks[i]}"), row=2, col=1, secondary_y=True)
for i in range(len(Ks)):
    plot_book(fig, i+3, bt_results, f"VOLCANIC_ROCK_VOUCHER_{Ks[i]}", "theo-devma", options={
        "plot_mid": False,
        "plot_position": True, 
        "plot_orderbook": True,
        "plot_bot_trades": True,
        "plot_own_trades": True,
        "plot_ma": False,
        "plot_theo": False,
    }, extras={
        "min_day": min(days),
        "a": a,
        "b": b,
        "c": c,
        "S": S,
        "K": Ks[i],
        "ma_window": 100,
    })
    # fig.add_trace(go.Scatter(x=timestamps, y=price_deviation[Ks[i]], mode="lines", name=f"d_{Ks[i]}", marker=dict(color=K_colors[i]), customdata=[Ks[i]], hovertemplate="time: %{x}<br>price deviation: %{y}"), row=i+3, col=1)
fig.update_layout(height=3200, hovermode="x", spikedistance=-1)
fig.update_yaxes(tickformat=".3f")
fig.update_xaxes(tickformat=".2f", showspikes=True, spikesnap="cursor", spikemode="across", spikedash="solid")
fig.update_xaxes(matches=None, row=1)
for i in range(2, 3+len(Ks)):
    fig.update_xaxes(matches='x2', row=i)
fig.show()