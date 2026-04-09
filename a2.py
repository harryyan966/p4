import matplotlib.pyplot as plt
from utils import *
from p4 import Trader

def relevant(trade):
    return trade.quantity >= 5

bt_states = get_trading_states_from_data("data", [0, 1])
reactions = backtest(Trader(), bt_states)
states = [reaction.input_state for reaction in reactions]
trades = [trade for reaction in reactions for trade in reaction.trades.get("make tomatoes", [])]
# trades = [trade for s in states for trade in s.market_trades.get("TOMATOES", []) + s.own_trades.get("TOMATOES", [])]
relevant_trades = [t for t in trades if relevant(t)]
print(f"Number of Trades: {len(trades)}, Relevance Ratio: {(len(relevant_trades) / len(trades)):.2f}")
fig, ax = plt.subplots(1, 1, figsize=(15, 5))
mids = {s.timestamp: get_wall_mid(s.order_depths.get("TOMATOES", OrderDepth())) for s in states}
# ax.plot(
#     [s.timestamp for s in states],
#     [get_wall_mid(s.order_depths.get("TOMATOES", OrderDepth())) for s in states],
#     color="blue"
# )
all_future_prices = []
for trade in relevant_trades:
    future_timestamps = [trade.timestamp + i * 100 for i in range(30)]
    if np.all(np.array(future_timestamps) <= max(mids.keys())):
        future_prices = np.array([mids[t] for t in future_timestamps])
        plt.plot(range(30), future_prices-future_prices[0])

# ax.scatter(
#     [t.timestamp for t in trades],
#     [t.price - mids[t.timestamp] for t in trades],
#     color="red"
# )
plt.savefig("image.png")