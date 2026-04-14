import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from utils import *
from p3 import Trader, PARAMETERS

bt_states = get_trading_states_from_data("data_p3/round1", [0, 1, 2], use_p3=True, use_cache=True)
bt_results = local_backtest(Trader(), bt_states, use_p3=True, parameters=PARAMETERS)
states = [r.input_state for r in bt_results]
pnl = [sum(p.values()) for p in get_pnls_from_reactions(bt_results)]
product = "SQUID_INK"

timestamps = [s.timestamp for s in states]
mids = [get_wall_mid(s.order_depths[product]) for s in states]
positions = [s.position.get(product, 0) for s in states]

window = 300
ma_pos = np.convolve(positions, np.ones(window)/window, mode='valid')
ma_timestamps = timestamps[window-1:]

own_trades = [t for r in bt_results for t in r.input_state.own_trades.get(product, [])]
buy_trades = [t for t in own_trades if t.buyer == "SUBMISSION"]
sell_trades = [t for t in own_trades if t.seller == "SUBMISSION"]
bot_trades = [t for r in bt_results for t in r.input_state.market_trades.get(product, []) if t.quantity > 5]
print(len(bot_trades))

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                    specs=[[{"secondary_y": True}], [{"secondary_y": False}]])

fig.add_trace(go.Scatter(x=timestamps, y=mids, name="mid", line=dict(color="blue")), row=1, col=1)
fig.add_trace(go.Scatter(x=[t.timestamp for t in buy_trades], y=[t.price for t in buy_trades],
    mode="markers", marker=dict(symbol="triangle-up", color="green", size=8), name="buy"), row=1, col=1)
fig.add_trace(go.Scatter(x=[t.timestamp for t in sell_trades], y=[t.price for t in sell_trades],
    mode="markers", marker=dict(symbol="triangle-down", color="red", size=8), name="sell"), row=1, col=1)
fig.add_trace(go.Scatter(x=[t.timestamp for t in bot_trades], y=[t.price for t in bot_trades],
    mode="markers", marker=dict(symbol="triangle-up", color="purple", size=8), name="bot_buy", customdata=[[t.quantity] for t in bot_trades],hovertemplate="time: %{x}<br>price: %{y}<br>qty: %{customdata[0]}"), row=1, col=1)
fig.add_trace(go.Scatter(x=[t.timestamp for t in bot_trades], y=[t.price for t in bot_trades],
    mode="markers", marker=dict(symbol="triangle-down", color="purple", size=8), name="bot_sell", customdata=[[t.quantity] for t in bot_trades],hovertemplate="time: %{x}<br>price: %{y}<br>qty: %{customdata[0]}<extra></extra>"), row=1, col=1)
fig.add_trace(go.Scatter(x=timestamps, y=positions, name="position", line=dict(color="orange")),
    row=1, col=1, secondary_y=True)
fig.add_trace(go.Scatter(x=ma_timestamps, y=list(ma_pos), name="position MA", line=dict(color="brown", dash="dash")),
    row=1, col=1, secondary_y=True)
fig.add_trace(go.Scatter(x=timestamps, y=pnl, name="pnl", line=dict(color="green")), row=2, col=1)

fig.update_layout(hovermode="x", spikedistance=-1)
fig.update_xaxes(showspikes=True, spikesnap="cursor", spikemode="across", spikedash="solid")

fig.show()