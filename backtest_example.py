"""
Backtesting Example
"""

from utils import *
from p4 import Trader

# states = get_trading_states_from_log("71415")
states = get_trading_states_from_data("data_p4", [0, 1], use_p3=False)
tomato_ma_window = 200
reactions = backtest(Trader(), states, use_p3=False, use_local=True, use_reasons=True,
                     parameters={"tomato ma window": tomato_ma_window})
pnls = get_pnls_from_reactions(reactions)

import matplotlib.pyplot as plt

fig, ax = plt.subplots(4, 1, figsize=(15, 24), dpi=300)
pnl_plot = ax[0]
pnl_plot.set_title("Backtest Results")
pnl_plot.set_xlabel("Timestamp")
pnl_plot.set_ylabel("Pnl")
pnl_plot.plot([sum(pnl.values()) for pnl in pnls], label="total pnl")
pnl_plot.plot([pnl.get("make tomatoes", 0) for pnl in pnls], label="make tomatoes")
pnl_plot.legend()

position_plot = ax[1]
position_plot.set_title("Positions")
position_plot.set_xlabel("Timestamp")
position_plot.set_ylabel("Position")
position_plot.plot([reaction.input_state.position.get("TOMATOES", 0) for reaction in reactions], label="position")
position_plot.legend()

price_plot = ax[2]
prices = [get_wall_mid(reaction.input_state.order_depths.get("TOMATOES", OrderDepth())) for reaction in reactions]
price_mas = calculate_moving_average(prices, window=tomato_ma_window)
price_plot.plot(prices)
price_plot.plot(price_mas)

ma_plot = ax[3]
ma_plot.plot(np.array(prices)-np.array(price_mas))

# orderbook_plot = ax[0]
# orders = [(reaction.input_state.timestamp, order) for reaction in reactions for reason, orders in reaction.orders.items() for order in orders]
# trades = [trade for reaction in reactions for reason, trades in reaction.trades.items() for trade in trades]
# market_trades = [trade for reaction in reactions for trade in reaction.input_state.market_trades.get("TOMATOES", [])]
# orderbook_plot.scatter(
#     [t for t,o in orders],
#     [o.price for t,o in orders],
#     marker = "*",
#     s = 1,
#     # color = ["green" if o.quantity > 0 else "red" for t,o in orders],
#     color="black"
# )
# orderbook_plot.scatter(
#     [t.timestamp+0.5 for t in trades if t.buyer == "SUBMISSION"],
#     [t.price for t in trades if t.buyer == "SUBMISSION"],
#     marker = "^",
#     s = [t.quantity*20 for t in trades if t.buyer == "SUBMISSION"],
#     color="green"
# )
# orderbook_plot.scatter(
#     [t.timestamp+0.5 for t in trades if t.seller == "SUBMISSION"],
#     [t.price for t in trades if t.seller == "SUBMISSION"],
#     marker = "v",
#     s = [t.quantity*20 for t in trades if t.seller == "SUBMISSION"],
#     color="red"
# )
# orderbook_plot.scatter(
#     [t.timestamp+0.5 for t in market_trades],
#     [t.price for t in market_trades],
#     marker = "+",
#     s = [t.quantity*50 for t in market_trades],
#     color="orange"
# )

# trade_histogram = ax[1]
# trade_histogram.hist([t.timestamp for t in trades if t.seller == "SUBMISSION"], color="red", bins=50)

# bid_histogram = ax[2]
# bid_histogram.hist([t.timestamp for t in trades if t.buyer == "SUBMISSION"], color="green", bins=50)


fig.savefig("image.png")


print(f"Total Pnl: {sum(pnls[-1].values())}")
print(f"Total Pnl from Making Tomatoes: {pnls[-1].get("make tomatoes", 0)}")