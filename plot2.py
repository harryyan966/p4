from utils import *
from p4 import Trader

# TODO: get pnl from each trade??

product = "TOMATOES"
# bt_states = get_trading_states_from_log("33608")
# bt_states = get_trading_states_from_data()
# assert len([trade for state in bt_states for trades in state.own_trades.values() for trade in trades]) == 0, "There are own trades" # TODO: incorporate own trades
# pnls, logs = backtest(Trader(), bt_states) # mine
# states = [log.state for log in logs.values()]
# print(max(pnls.items()))
# print(len(bt_states))
states = get_trading_states_from_log("39231")
pnls = get_pnls_from_trading_states(states)

def get_mid(state: TradingState):
    b = min(state.order_depths[product].buy_orders.keys())
    s = max(state.order_depths[product].sell_orders.keys())
    return (b + s) / 2

def get_best_ask(state: TradingState):
    return min(state.order_depths[product].sell_orders.keys())

def get_best_bid(state: TradingState):
    return max(state.order_depths[product].buy_orders.keys())

def get_wall_ask(state: TradingState):
    return sorted(state.order_depths[product].sell_orders.keys())[-2]

def get_wall_bid(state: TradingState):
    return sorted(state.order_depths[product].buy_orders.keys())[1]

def get_trade_size(state: TradingState):
    return sum([t.quantity for t in state.market_trades.get(product, [])])

def get_middle_orders(state: TradingState):
    b = sorted(state.order_depths[product].buy_orders.items())[2:]
    s = sorted(state.order_depths[product].sell_orders.items())[:-2]
    return [(state.timestamp, p, q) for p, q in b + s]

def get_mid_size(state: TradingState):
    return sum([o[2] for o in get_middle_orders(state)])



import matplotlib.pyplot as plt

fig, ax = plt.subplots(3, 1, figsize=(30,30), dpi=200)

ax[0].plot(
    [s.timestamp for s in states],
    [get_mid(s) for s in states]
)

ax[0].plot(
    [s.timestamp for s in states],
    [get_wall_ask(s) for s in states],
    color="red"
)

ax[0].plot(
    [s.timestamp for s in states],
    [get_wall_bid(s) for s in states],
    color="green"
)

trades = sum([s.own_trades.get(product, []) for s in states], [])
# trades = [t for t in trades if t.quantity == 5]

ax[0].scatter(
    [t.timestamp for t in trades],
    [t.price for t in trades],
    s = [abs(t.quantity) * 50 for t in trades],
    c = ["green" if t.buyer == "" else "red" for t in trades],
    marker = "o"
)

middle_orders = []
for s in states:
    m = get_mid(s)
    for x in get_middle_orders(s):
        # if x[1] < m and x[2] < 0 or x[1] > m and x[2] > 0:
        middle_orders.append(x)

ax[0].scatter(
    [x[0] for x in middle_orders],
    [x[1] for x in middle_orders],
    s = [abs(x[2]) * 50 for x in middle_orders],
    facecolors = "none",
    edgecolors = ["green" if x[2] > 0 else "red" for x in middle_orders],
)

# print([(x[0], x[2]) for x in middle_orders])

bot_trades = sum([s.market_trades.get(product, []) for s in states], [])
# bot_trades = [t for t in bot_trades if t.quantity == 5]

ax[0].scatter(
    [t.timestamp for t in bot_trades],
    [t.price for t in bot_trades],
    s = [abs(t.quantity) * 50 for t in bot_trades],
    c = "blue",
    marker = "x"
)

ax[1].plot(
    [s.timestamp for s in states],
    [s.position.get(product, 0) for s in states]
)

ax[2].plot(
    [t.timestamp for t in states],
    [pnls[t.timestamp] for t in states]
)

# colors = {0: "red", 1: "orange", 2: "brown", 3: "green", 4: "blue", 5: "indigo", 6: "violet"}

# ax[0].scatter(
#     [s.timestamp for s in states if s.market_trades.get(product, [])],
#     [get_mid(s) for s in states if s.market_trades.get(product, [])],
#     s=[get_trade_size(s) * 30 for s in states if s.market_trades.get(product, [])],
#     c=[colors[get_trade_size(s) % 7] for s in states if s.market_trades.get(product, [])],
#     marker="o"
# )

# for t in [s.timestamp for s in states if get_trade_size(s) != 0]:
#     ax[0].axvline(t, color="red")

# ax[1].plot(
#     [s.timestamp for s in states],
#     [significant(s, 5) for s in states]
# )

# for q in set([get_trade_size(s) for s in states]):
#     ax[1].axhline(q, color="red")

# ax[1].scatter(
#     [s.timestamp for s in states if get_mid_size(s) != 0],
#     [get_mid(s) for s in states if get_mid_size(s) != 0],
#     s=[abs(get_mid_size(s)) * 20 for s in states if get_mid_size(s) != 0],
#     c=[colors[abs(get_trade_size(s)) % 7] for s in states if get_mid_size(s) != 0],
#     marker="o"
# )


plt.savefig("image.png")