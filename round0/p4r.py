import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from utils import *
from p4 import Trader, PARAMETERS

PLOT_ORDERBOOK = True
PLOT_BOT_TRADES = False
def plot_own_trade(trade):
    return True

bt_states = get_trading_states_from_log("71415")
# bt_states = get_trading_states_from_data("data_p4", [0, 1], use_p3=False, use_cache=True)
bt_results = local_backtest(Trader(), bt_states, use_p3=False, parameters=PARAMETERS)
states = [r.input_state for r in bt_results]
pnl = [sum(p.values()) for p in get_pnls_from_reactions(bt_results)]
product = "TOMATOES"
making_positions = [int(r.logs["trade_tomatoes"]["making position"]) for r in bt_results]
print(bt_results[-1].logs)

timestamps = [s.timestamp for s in states]
mids = [get_wall_mid(s.order_depths[product]) for s in states]
positions = [s.position.get(product, 0) for s in states]

window = PARAMETERS["tomato ma window"]
ma_pos = np.convolve(mids, np.ones(window)/window, mode='valid')
ma_timestamps = timestamps[window-1:]

own_trades = [(reason,t) for r in bt_results for reason, trades in r.trades.items() for t in trades if t.symbol == product and plot_own_trade(t)]
buy_trades = [(r,t) for r,t in own_trades if t.buyer == "SUBMISSION"]
sell_trades = [(r,t) for r,t in own_trades if t.seller == "SUBMISSION"]
bot_trades = [t for r in bt_results for t in r.input_state.market_trades.get(product, [])]
print(len(bot_trades))

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                    specs=[[{"secondary_y": True}], [{"secondary_y": False}]])
                    

fig.add_trace(go.Scatter(x=timestamps, y=mids, name="mid", line=dict(color="blue")), row=1, col=1)
fig.add_trace(go.Scatter(x=[t.timestamp for r,t in buy_trades], y=[t.price for r,t in buy_trades],
    mode="markers", marker=dict(symbol="triangle-up", color="green", size=8), name="buy", customdata=[[t.quantity, r] for r,t in buy_trades],hovertemplate="time: %{x}<br>price: %{y}<br>qty: %{customdata[0]}<br>reason: %{customdata[1]}"), row=1, col=1)
fig.add_trace(go.Scatter(x=[t.timestamp for r,t in sell_trades], y=[t.price for r,t in sell_trades],
    mode="markers", marker=dict(symbol="triangle-down", color="red", size=8), name="sell", customdata=[[t.quantity, r] for r,t in sell_trades],hovertemplate="time: %{x}<br>price: %{y}<br>qty: %{customdata[0]}<br>reason: %{customdata[1]}"), row=1, col=1)
# fig.add_trace(go.Scatter(x=[t.timestamp for t in bot_trades], y=[t.price for t in bot_trades],
#     mode="markers", marker=dict(symbol="triangle-up", color="purple", size=8), name="bot_buy", customdata=[[t.quantity] for t in bot_trades],hovertemplate="time: %{x}<br>price: %{y}<br>qty: %{customdata[0]}"), row=1, col=1)
if PLOT_BOT_TRADES: fig.add_trace(go.Scatter(x=[t.timestamp for t in bot_trades], y=[t.price for t in bot_trades],
    mode="markers", marker=dict(symbol="cross", color="purple", size=8), name="bot_trade", customdata=[[t.quantity] for t in bot_trades],hovertemplate="time: %{x}<br>price: %{y}<br>qty: %{customdata[0]}<extra></extra>"), row=1, col=1)
fig.add_trace(go.Scatter(x=timestamps, y=positions, name="position", line=dict(color="orange")),
    row=1, col=1, secondary_y=True)
fig.add_trace(go.Scatter(x=timestamps, y=making_positions, name="making position", line=dict(color="cyan")),
    row=1, col=1, secondary_y=True)
fig.add_trace(go.Scatter(x=ma_timestamps, y=list(ma_pos), name="mid MA", line=dict(color="brown", dash="dash")),
    row=1, col=1, secondary_y=False)
fig.add_trace(go.Scatter(x=timestamps, y=pnl, name="pnl", line=dict(color="green")), row=2, col=1)

for i in range(3) if PLOT_ORDERBOOK else []:
    opacity = 0.6 - i * 0.2
    bid_prices = [sorted(s.order_depths[product].buy_orders.keys(), reverse=True)[i] 
                  if len(s.order_depths[product].buy_orders) > i else None for s in states]
    ask_prices = [sorted(s.order_depths[product].sell_orders.keys())[i] 
                  if len(s.order_depths[product].sell_orders) > i else None for s in states]
    bid_vols = [s.order_depths[product].buy_orders[p] if p is not None else None for p, s in zip(bid_prices, states)]
    ask_vols = [abs(s.order_depths[product].sell_orders[p]) if p is not None else None for p, s in zip(ask_prices, states)]

    fig.add_trace(go.Scatter(x=timestamps, y=bid_prices, mode="markers",
        marker=dict(symbol="circle", color=f"rgba(0,180,0,{opacity})", size=4),
        name=f"bid{i+1}", customdata=bid_vols,
        hovertemplate=f"bid{i+1}: %{{y}} x %{{customdata}}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=timestamps, y=ask_prices, mode="markers",
        marker=dict(symbol="circle", color=f"rgba(220,0,0,{opacity})", size=4),
        name=f"ask{i+1}", customdata=ask_vols,
        hovertemplate=f"ask{i+1}: %{{y}} x %{{customdata}}<extra></extra>"), row=1, col=1)

with open("p4.py", "r") as f:
    fig.add_annotation(
        text=f.read(),
        xref="paper", yref="paper",
        x=0, y=-0.1,
        showarrow=False,
        font=dict(family="monospace", size=12),
        align="left"
    )

fig.update_layout(height=1200, hovermode="x", spikedistance=-1)
fig.update_xaxes(showspikes=True, spikesnap="cursor", spikemode="across", spikedash="solid")

fig.show()