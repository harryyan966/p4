from utils import *
from p4 import Trader
import matplotlib.pyplot as plt

def get_mid(state: TradingState, product):
    b = min(state.order_depths[product].buy_orders.keys())
    s = max(state.order_depths[product].sell_orders.keys())
    return (b + s) / 2

def get_best_ask(state: TradingState, product):
    return min(state.order_depths[product].sell_orders.keys())

def get_best_bid(state: TradingState, product):
    return max(state.order_depths[product].buy_orders.keys())

def get_wall_ask(state: TradingState, product):
    return sorted(state.order_depths[product].sell_orders.keys())[-2]

def get_wall_bid(state: TradingState, product):
    return sorted(state.order_depths[product].buy_orders.keys())[1]

def get_trade_size(state: TradingState, product):
    return sum([t.quantity for t in state.market_trades.get(product, [])])

def get_middle_orders(state: TradingState, product):
    b = sorted(state.order_depths[product].buy_orders.items())[2:]
    s = sorted(state.order_depths[product].sell_orders.items())[:-2]
    return [(state.timestamp, p, q) for p, q in b + s]

def get_mid_size(state: TradingState, product):
    return sum([o[2] for o in get_middle_orders(state, product)])

def plot_mid(ax, states, product):
    ax.plot(
        [s.timestamp for s in states],
        [get_mid(s, product) for s in states]
    )

def plot_small_ask_wall(ax, states, product):
    ax.plot(
        [s.timestamp for s in states],
        [get_wall_ask(s, product) for s in states],
        color="red"
    )

def plot_small_bid_wall(ax, states, product):
    ax.plot(
        [s.timestamp for s in states],
        [get_wall_bid(s, product) for s in states],
        color="green"
    )

def scatter_own_trades(ax, states, product):
    trades = sum([s.own_trades.get(product, []) for s in states], [])
    ax.scatter(
        [t.timestamp for t in trades],
        [t.price for t in trades],
        s = [abs(t.quantity) * 50 for t in trades],
        c = ["green" if t.buyer == "" else "red" for t in trades],
        marker = "o"
    )

def scatter_middle_orders(ax, states, product):
    middle_orders = [order for s in states for order in get_middle_orders(s, product)]
    ax.scatter(
        [x[0] for x in middle_orders],
        [x[1] for x in middle_orders],
        s = [abs(x[2]) * 50 for x in middle_orders],
        facecolors = "none",
        edgecolors = ["green" if x[2] > 0 else "red" for x in middle_orders],
    )

def scatter_bot_trades(ax, states, product):
    bot_trades = sum([s.market_trades.get(product, []) for s in states], [])
    ax.scatter(
        [t.timestamp for t in bot_trades],
        [t.price for t in bot_trades],
        s = [abs(t.quantity) * 50 for t in bot_trades],
        c = "blue",
        marker = "x"
    )

def plot_position(ax, states, product):
    ax.plot(
        [s.timestamp for s in states],
        [s.position.get(product, 0) for s in states]
    )

def plot_pnls(ax, states, pnls, product):
    ax.plot(
        [t.timestamp for t in states],
        [pnls[product][t.timestamp] for t in states]
    )



def visualize(states, pnls, product):
    fig, ax = plt.subplots(3, 1, figsize=(30,30), dpi=200)

    plot_mid(ax[0], states, product)
    plot_small_ask_wall(ax[0], states, product)
    plot_small_bid_wall(ax[0], states, product)
    scatter_bot_trades(ax[0], states, product)
    scatter_own_trades(ax[0], states, product)
    scatter_middle_orders(ax[0], states, product)
    
    plot_position(ax[1], states, product)
    plot_pnls(ax[2], states, pnls, product)

    fig.savefig("image.png")
    

def visualize_log(log_id, product):
    states = get_trading_states_from_log(log_id)
    pnls = get_pnls_from_trading_states(states)
    visualize(states, pnls, product)

def backtest_on_log_data_and_visualize(trader, log_id, product):
    bt_states = get_trading_states_from_log(log_id) # 33608
    assert len([trade for state in bt_states for trades in state.own_trades.values() for trade in trades]) == 0, "There are own trades" # TODO: incorporate own trades
    pnls, logs = backtest(trader, bt_states) # TODO: cache backtest
    states = [log.state for log in logs.values()]
    visualize(states, pnls, product)

def backtest_on_full_data_and_visualize(trader, product):
    bt_states = get_trading_states_from_data()
    pnls, logs = backtest(trader, bt_states) # TODO: cache backtest
    states = [log.state for log in logs.values()]
    visualize(states, pnls, product)


# TODO: get pnl from each trade??
backtest_on_full_data_and_visualize(Trader(), "TOMATOES")