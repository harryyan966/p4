import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from utils import *
from p3 import Trader, PARAMETERS

# Grab States

use_cache = True
bt_states = get_trading_states_from_data("data_p3/round3", [2, 3, 4], use_p3=True, use_cache=use_cache)
# bt_results = local_backtest(Trader(), bt_states, use_p3=True, parameters=PARAMETERS)
# states = [r.input_state for r in bt_results]
states = bt_states
timestamps = np.array([s.timestamp for s in states])
S = np.array([get_wall_mid(s.order_depths.get("VOLCANIC_ROCK", OrderDepth())) for s in states])
days_left = 5
TTE = days_left - timestamps / 10000_00

import math
from scipy.optimize import brentq


def _norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def _bs_price(S, K, T, r, sigma):
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)

def implied_vol(V, S, K, TTE, r=0.0, tol=1e-6):
    try:
        return brentq(lambda sigma: _bs_price(S, K, TTE, r, sigma) - V, 1e-6, 10.0, xtol=tol)
    except ValueError:
        return np.nan

implied_vol_vec = np.vectorize(implied_vol)

Ks = [9500, 9750, 10000, 10250, 10500]
m = {}
V = {}
sigma = {}
for K in tqdm(Ks):
    m[K] = np.log(K / S) / np.sqrt(days_left - timestamps / 1_000_000)
    V[K] = np.array([get_wall_mid(s.order_depths.get(f"VOLCANIC_ROCK_VOUCHER_{K}", OrderDepth())) for s in states])
    sigma[K] = implied_vol_vec(V[K], S, K, TTE)

ms = np.array([mi for K in Ks for mi in m[K]])
sigmas = np.array([mi for K in Ks for mi in sigma[K]])
xy = np.array([[mi, sigmai] for mi, sigmai in zip(ms, sigmas) if sigmai > 0])
a, b, c = np.polyfit(xy[:,0], xy[:,1], 2)
sigma_baselines = a*ms**2 + b*ms + c

fig = make_subplots(rows=1, cols=1, shared_xaxes=True, vertical_spacing=0.05, specs=[[{"secondary_y": True}]])
for i in tqdm(range(len(Ks))):
    fig.add_trace(go.Scatter(x=m[Ks[i]], y=sigma[Ks[i]], mode="markers", marker=dict(symbol="circle", color=["blue", "red", "green", "purple", "orange"][i], size=8), name=f"{Ks[i]}", customdata=[[t] for t in timestamps],hovertemplate="time: %{customdata[0]}<br>implied vol: %{y}"), row=1, col=1)
fig.add_trace(go.Scatter(x=ms, y=sigma_baselines, mode="lines"))
fig.update_yaxes(tickformat=".3f")
fig.show()