from utils import *
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

class Plotter:
    def __init__(self, states: list[TradingState], product: str, baseline_prices: list[float]):
        for i in range(len(states)-1):
            assert states[i+1].timestamp - states[i].timestamp == 100
        self.states = states
        self.product = product
        self.baseline = baseline_prices
    
    def plot_mid(self, ax):
        ax.plot(
            [s.timestamp for s in self.states],
            [get_mid(s, self.product) - p for s, p in zip(self.states, self.baseline)]
        )
    
    def plot_first_ask_wall(self, ax):
        ax.plot(
            [s.timestamp for s in self.states],
            [get_wall_ask(s, self.product) - p for s, p in zip(self.states, self.baseline)],
            color="red"
        )
    def plot_first_bid_wall(self, ax):
        ax.plot(
            [s.timestamp for s in self.states],
            [get_wall_bid(s, self.product) - p for s, p in zip(self.states, self.baseline)],
            color="green"
        )
    
    def scatter_own_trades(self, ax):
        trades = [(t,p) for s,p in zip(self.states, self.baseline) for t in s.own_trades.get(self.product, [])]
        ax.scatter(
            [t[0].timestamp for t in trades],
            [t[0].price - t[1] for t in trades],
            s = [abs(t[0].quantity) * 50 for t in trades],
            c = ["green" if t[0].buyer == "" else "red" for t in trades],
            marker = "o"
        )

    def scatter_middle_orders(self, ax):
        middle_orders = [(order, p) for s,p in zip(self.states, self.baseline) for order in get_middle_orders(s, self.product)]
        ax.scatter(
            [x[0][0] for x in middle_orders],
            [x[0][1]-x[1] for x in middle_orders],
            s = [abs(x[0][2]) * 50 for x in middle_orders],
            facecolors = "none",
            edgecolors = ["green" if x[0][2] > 0 else "red" for x in middle_orders],
        )

    def scatter_bot_trades(self, ax):
        bot_trades = [(t, p) for s,p in zip(self.states, self.baseline) for t in s.market_trades.get(self.product, [])]
        ax.scatter(
            [t[0].timestamp for t in bot_trades],
            [t[0].price - t[1] for t in bot_trades],
            s = [abs(t[0].quantity) * 50 for t in bot_trades],
            c = "blue",
            marker = "x"
        )

    def plot_position(self, ax):
        ax.plot(
            [s.timestamp for s in self.states],
            [s.position.get(self.product, 0) for s in self.states]
        )

    def plot_pnls(self, ax, pnls):
        ax.plot(
            [t.timestamp for t in self.states],
            [pnls[t.timestamp//100] for t in self.states]
        )
    
    def plot_price_delta_ma(self, ax, window=50):
        price_deltas = [
            0 if i == 0
            else get_mid(self.states[i], self.product)
            - get_mid(self.states[i-1], self.product)
            for i in range(len(self.states))
        ]

        ax.plot(
            [t.timestamp for t in self.states],
            calculate_moving_average(price_deltas, window, pad_front=0)
        )



def visualize(states, pnls, product):
    fig, ax = plt.subplots(5, 1, figsize=(20,40), dpi=100)
    # p = Plotter(states, product, [0 for _ in states])
    p = Plotter(states, product, [get_mid(s, product) for s in states])
    p_raw = Plotter(states, product, [0 for _ in states])

    ax[0].set_title("Microstructure")
    p.plot_mid(ax[0])
    p.plot_first_ask_wall(ax[0])
    p.plot_first_bid_wall(ax[0])
    p.scatter_bot_trades(ax[0])
    # p.scatter_own_trades(ax[0])
    p.scatter_middle_orders(ax[0])

    ax[1].set_title("Position")
    p.plot_position(ax[1])

    ax[2].set_title("Pnl")
    p.plot_pnls(ax[2], pnls)

    ax[3].set_title("Price Change Moving Average")
    p.plot_price_delta_ma(ax[3])

    ax[4].set_title("Price")
    p_raw.plot_mid(ax[4])

    fig.savefig("image.png")
    
def visualize_log(log_id, product):
    states = get_trading_states_from_log(log_id)
    pnls = get_pnls_from_trading_states(states)
    visualize(states, pnls, product)

def backtest_on_log_data_and_visualize(trader, log_id, product):
    bt_states = get_trading_states_from_log(log_id) # 33608
    assert len([trade for state in bt_states for trades in state.own_trades.values() for trade in trades]) == 0, "There are own trades" # TODO: incorporate own trades
    reactions = backtest(trader, bt_states) # TODO: cache backtest
    states = [reaction.input_state for reaction in reactions]
    all_pnls = get_pnls_from_reactions(reactions)
    total_pnls = [sum(pnl.values()) for pnl in all_pnls]
    visualize(states, total_pnls, product)

def backtest_on_full_data_and_visualize(trader, product, min_t=0, max_t=9000000):
    bt_states = get_trading_states_from_data(min_t, max_t)
    reactions = backtest(trader, bt_states) # TODO: cache backtest
    states = [reaction.input_state for reaction in reactions]
    all_pnls = get_pnls_from_reactions(reactions)
    total_pnls = [sum(pnl.values()) for pnl in all_pnls]
    visualize(states, total_pnls, product)


# Doesn't Quite Work Here
from p4 import Trader
backtest_on_full_data_and_visualize(Trader(), "TOMATOES", 0, 200000)