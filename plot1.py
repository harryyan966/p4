
from utils import *

product = "TOMATOES"
logs = get_trader_logs("33608")
states = [get_relevant_state(log.state) for _, log in sorted(logs.items())]
def get_mid(state: TradingState):
    b = min(state.order_depths[product].buy_orders.keys())
    s = max(state.order_depths[product].sell_orders.keys())
    return (b + s) / 2

import matplotlib.pyplot as plt

fig, ax = plt.subplots(2, 1, figsize=(30,10), dpi=300)
ax[0].plot([s.timestamp for s in states], [get_mid(s) for s in states])

def get_trade_size(state: TradingState):
    return sum([t.quantity for t in state.market_trades.get(product, [])])

colors = {0: "red", 1: "orange", 2: "brown", 3: "green", 4: "blue", 5: "indigo", 6: "violet"}

ax[0].scatter(
    [s.timestamp for s in states if s.market_trades.get(product, [])],
    [get_mid(s) for s in states if s.market_trades.get(product, [])],
    s=[get_trade_size(s) * 30 for s in states if s.market_trades.get(product, [])],
    c=[colors[get_trade_size(s) % 7] for s in states if s.market_trades.get(product, [])],
    marker="o"
)


def get_mid_size(state: TradingState):
    b = sorted(state.order_depths[product].buy_orders.items())[2:]
    s = sorted(state.order_depths[product].sell_orders.items())[:-2]
    return sum([q for _, q in b + s])

for t in [s.timestamp for s in states if get_trade_size(s) != 0]:
    ax[0].axvline(t, color="red")

ax[1].plot(
    [s.timestamp for s in states],
    [get_trade_size(s) for s in states]
)

for q in set([get_trade_size(s) for s in states]):
    ax[1].axhline(q, color="red")

# ax[1].scatter(
#     [s.timestamp for s in states if get_mid_size(s) != 0],
#     [get_mid(s) for s in states if get_mid_size(s) != 0],
#     s=[abs(get_mid_size(s)) * 20 for s in states if get_mid_size(s) != 0],
#     c=[colors[abs(get_trade_size(s)) % 7] for s in states if get_mid_size(s) != 0],
#     marker="o"
# )


plt.savefig("image.png")