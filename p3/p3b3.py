import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from utils import *
from p3.p3 import Trader, PARAMETERS
from trash.plot_lib import plot_book

days = [3, 4, 5, 6]
a,b,c = []
bt_states = get_trading_states_from_data("data_p3/all", days, use_p3=True, use_cache=True)
# bt_results = local_backtest(Trader(), bt_states, use_p3=True, parameters=bt_parameters)
bt_results = [Reaction(s, "", {}, {}) for s in bt_states]
states = [r.input_state for r in bt_results]
pnl = [sum(p.values()) if None not in p.values() else None for p in get_pnls_from_reactions(bt_results)]
timestamps = [s.timestamp for s in states]
product = "VOLCANIC_ROCK_VOUCHER_10000"
S = fill_backward(fill_forward([get_strict_wall_mid(s.order_depths["VOLCANIC_ROCK"]) for s in states]))

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                    specs=[[{"secondary_y": True}], [{"secondary_y": False}]])
Ks = [9500, 9750, 10000, 10250, 10500]
for i in range(len(Ks)):
    plot_book(fig, i+1, bt_results, f"VOLCANIC_ROCK_VOUCHER{Ks[i]}", "zero", options={
        "plot_mid": True,
        "plot_position": True, 
        "plot_orderbook": True,
        "plot_bot_trades": True,
        "plot_own_trades": True,
        "plot_ma": False,
    }, extras={
        "min_day": min(days),
        "a": a,
        "b": b,
        "c": c,
        "S": S,
        "K": Ks[i],
    })
fig.add_trace(go.Scatter(x=timestamps, y=pnl, name="pnl"), row=2, col=1)
with open("p4.py", "r") as f:
    code = f.read()
fig.add_annotation(
    text=code,
    xref="paper", yref="paper",
    x=0, y=-0.1,
    showarrow=False,
    font=dict(family="monospace", size=12),
    align="left"
)
fig.update_layout(height=1200, hovermode="x", spikedistance=-1)
fig.update_xaxes(showspikes=True, spikesnap="cursor", spikemode="across", spikedash="solid")
fig.show()