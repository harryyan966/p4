import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from utils import *
from p3 import Trader, PARAMETERS

PLOT_MID = False
PLOT_POSITION = True
PLOT_ORDERBOOK = True
PLOT_BOT_TRADES = True
def plot_own_trade(trade):
    return True

use_cache = True
bt_states = get_trading_states_from_data("data_p3/round3", [2, 3, 4], use_p3=True, use_cache=use_cache)
# bt_states = get_trading_states_from_data("data_p3/eval", [2], use_p3=True, use_cache=use_cache)
bt_results = local_backtest(Trader(), bt_states, use_p3=True, parameters=PARAMETERS)
states = [r.input_state for r in bt_results]
pnl = [sum(p.values()) if None not in p.values() else None for p in get_pnls_from_reactions(bt_results)]
product = "PICNIC_BASKET1"
timestamps = [s.timestamp for s in states]
mids = fill_backward(fill_forward([get_strict_wall_mid(s.order_depths[product]) for s in states]))
assert None not in mids
c = fill_backward(fill_forward([get_strict_wall_mid(s.order_depths["CROISSANTS"]) for s in states]))
assert None not in mids
j = fill_backward(fill_forward([get_strict_wall_mid(s.order_depths["JAMS"]) for s in states]))
assert None not in mids
d = fill_backward(fill_forward([get_strict_wall_mid(s.order_depths["DJEMBES"]) for s in states]))
assert None not in mids
positions = [s.position.get(product, 0) for s in states]
# window = 30
# ma_pos = calculate_moving_average(mids, window=window, pad_front=None)
# ma_timestamps = timestamps[window-1:]
# baseline = [0] * len(states)
baseline = np.array(c) * 6 + np.array(j) * 3 + np.array(d) * 1
# baseline = np.array(timestamps)* 0.001 + 10000
baseline = np.array(baseline)
def rel(values):
    return [v-b if v is not None else None for v, b in zip(values, baseline)]

def rel_trade(trade):
    return Trade(
        symbol=trade.symbol,
        price=trade.price-baseline[trade.timestamp//100],
        quantity=trade.quantity,
        buyer=trade.buyer,
        seller=trade.seller,
        timestamp=trade.timestamp
    )

def rel_trades(trades):
    return [rel_trade(t) for t in trades]

own_trades = [(reason,t) for r in bt_results for reason, trades in r.trades.items() for t in trades if t.symbol == product and plot_own_trade(t)]
buy_trades = [(r,t) for r,t in own_trades if t.buyer == "SUBMISSION"]
sell_trades = [(r,t) for r,t in own_trades if t.seller == "SUBMISSION"]
bot_trades = [t for r in bt_results for t in r.input_state.market_trades.get(product, [])]
print(len(bot_trades))

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                    specs=[[{"secondary_y": True}], [{"secondary_y": False}]])

if PLOT_MID: fig.add_trace(go.Scatter(x=timestamps, y=rel(mids), name="mid", line=dict(color="blue")), row=1, col=1)
mean_premium = [r.logs["trade_basket2"].get("mean_premium",0) for r in bt_results]
fig.add_trace(go.Scatter(x=timestamps, y=mean_premium, name="mean_premium", line=dict(color="blue")), row=1, col=1)
fig.add_trace(go.Scatter(x=[t.timestamp for r,t in buy_trades], y=[rel_trade(t).price for r,t in buy_trades],
    mode="markers", marker=dict(symbol="triangle-up", color="green", size=8), name="buy", customdata=[[t.quantity, r] for r,t in buy_trades],hovertemplate="time: %{x}<br>price: %{y}<br>qty: %{customdata[0]}<br>reason: %{customdata[1]}"), row=1, col=1)
fig.add_trace(go.Scatter(x=[t.timestamp for r,t in sell_trades], y=[rel_trade(t).price for r,t in sell_trades],
    mode="markers", marker=dict(symbol="triangle-down", color="red", size=8), name="sell", customdata=[[t.quantity, r] for r,t in sell_trades],hovertemplate="time: %{x}<br>price: %{y}<br>qty: %{customdata[0]}<br>reason: %{customdata[1]}"), row=1, col=1)
# fig.add_trace(go.Scatter(x=[t.timestamp for t in bot_trades], y=[t.price for t in bot_trades],
#     mode="markers", marker=dict(symbol="triangle-up", color="purple", size=8), name="bot_buy", customdata=[[t.quantity] for t in bot_trades],hovertemplate="time: %{x}<br>price: %{y}<br>qty: %{customdata[0]}"), row=1, col=1)
if PLOT_BOT_TRADES: fig.add_trace(go.Scatter(x=[t.timestamp for t in bot_trades], y=[rel_trade(t).price for t in bot_trades],
    mode="markers", marker=dict(symbol="cross", color="purple", size=8), name="bot_trade", customdata=[[t.quantity] for t in bot_trades],hovertemplate="time: %{x}<br>price: %{y}<br>qty: %{customdata[0]}<extra></extra>"), row=1, col=1)
if PLOT_POSITION: fig.add_trace(go.Scatter(x=timestamps, y=positions, name="position", line=dict(color="orange")),
    row=1, col=1, secondary_y=True)
# fig.add_trace(go.Scatter(x=timestamps, y=making_positions, name="making position", line=dict(color="cyan")),
    # row=1, col=1, secondary_y=True)
# fig.add_trace(go.Scatter(x=ma_timestamps, y=rel(ma_pos), name="mid MA", line=dict(color="brown", dash="dash")),
    # row=1, col=1, secondary_y=False)
fig.add_trace(go.Scatter(x=timestamps, y=pnl, name="pnl", line=dict(color="green")), row=2, col=1)

# time = np.array(timestamps) // 100
# bid_dist = rel([int(x) for x in baseline - 5 - np.linspace(0, 1.5, 30000)])
# ask_dist = rel([int(x) for x in baseline + 6 + np.linspace(0, 1.5, 30000)])
# fig.add_trace(go.Scatter(x=timestamps, y=bid_dist, name="bid dist", line=dict(color="blue")), row=1, col=1)
# fig.add_trace(go.Scatter(x=timestamps, y=ask_dist, name="ask dist", line=dict(color="blue")), row=1, col=1)




for i in range(3) if PLOT_ORDERBOOK else []:
    opacity = 0.6 - i * 0.2
    bid_prices = [sorted(s.order_depths[product].buy_orders.keys(), reverse=True)[i] 
                  if len(s.order_depths[product].buy_orders) > i else None for s in states]
    ask_prices = [sorted(s.order_depths[product].sell_orders.keys())[i] 
                  if len(s.order_depths[product].sell_orders) > i else None for s in states]
    bid_vols = [s.order_depths[product].buy_orders[p] if p is not None else None for p, s in zip(bid_prices, states)]
    ask_vols = [abs(s.order_depths[product].sell_orders[p]) if p is not None else None for p, s in zip(ask_prices, states)]

    fig.add_trace(go.Scatter(x=timestamps, y=rel(bid_prices), mode="markers",
        line=dict(color=f"rgba(0,180,0,{opacity})", width=1),
        name=f"bid{i+1}", customdata=bid_vols,
        hovertemplate=f"bid{i+1}: %{{customdata}} @ %{{y}}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=timestamps, y=rel(ask_prices), mode="markers",
        line=dict(color=f"rgba(220,0,0,{opacity})", width=1),
        name=f"ask{i+1}", customdata=ask_vols,
        hovertemplate=f"ask{i+1}: %{{customdata}} @ %{{y}}<extra></extra>"), row=1, col=1)
# for i in range(3) if PLOT_ORDERBOOK else []:
#     opacity = 0.6 - i * 0.2
#     bid_prices = [sorted(s.order_depths[product].buy_orders.keys(), reverse=True)[i] 
#                   if len(s.order_depths[product].buy_orders) > i else None for s in states]
#     ask_prices = [sorted(s.order_depths[product].sell_orders.keys())[i] 
#                   if len(s.order_depths[product].sell_orders) > i else None for s in states]
#     bid_vols = [s.order_depths[product].buy_orders[p] if p is not None else None for p, s in zip(bid_prices, states)]
#     ask_vols = [abs(s.order_depths[product].sell_orders[p]) if p is not None else None for p, s in zip(ask_prices, states)]

#     fig.add_trace(go.Scatter(x=timestamps, y=rel(bid_prices), mode="lines",
#         line=dict(color=f"rgba(0,180,0,{opacity})", width=1),
#         name=f"bid{i+1}", customdata=bid_vols,
#         hovertemplate=f"bid{i+1}: %{{customdata}} @ %{{y}}<extra></extra>"), row=1, col=1)
#     fig.add_trace(go.Scatter(x=timestamps, y=rel(ask_prices), mode="lines",
#         line=dict(color=f"rgba(220,0,0,{opacity})", width=1),
#         name=f"ask{i+1}", customdata=ask_vols,
#         hovertemplate=f"ask{i+1}: %{{customdata}} @ %{{y}}<extra></extra>"), row=1, col=1)

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