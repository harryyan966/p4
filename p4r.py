import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from utils import *
from p4 import Trader, PARAMETERS

PLOT_ORDERBOOK = False
PLOT_BOT_TRADES = True
def plot_own_trade(trade):
    return True

bt_states = get_trading_states_from_data("data_p4/round1", [0, 1, 2], use_p3=False, use_cache=True)
bt_results = local_backtest(Trader(), bt_states, use_p3=False, parameters=PARAMETERS)
states = [r.input_state for r in bt_results]
pnl = [sum(p.values()) if None not in p.values() else None for p in get_pnls_from_reactions(bt_results)]
product = "ASH_COATED_OSMIUM"
# product = "INTARIAN_PEPPER_ROOT"

timestamps = [s.timestamp for s in states]
mids = [get_strict_wall_mid(s.order_depths[product]) for s in states]
positions = [s.position.get(product, 0) for s in states]

xy = np.array([(t,m) for t,m in zip(timestamps, mids) if m is not None])

# f = np.poly1d(np.polyfit(xy[:,0],xy[:,1],1))
beta, alpha = np.polyfit(xy[:,0],xy[:,1],1)
print(beta, alpha)

fig = make_subplots(rows=1, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                    specs=[[{"secondary_y": False}]])

fig.add_trace(go.Scatter(x=xy[:,0], y=xy[:,1], mode="markers", marker=dict(symbol="circle", color="blue", size=8), name="mid", hovertemplate="time: %{x}<br>price: %{y}"), row=1, col=1)
fig.add_trace(go.Scatter(x=xy[:,0], y=[beta*x+alpha if x is not None else None for x in xy[:,0]], name="prices", line=dict(color="red")), row=1, col=1)

fig.show()