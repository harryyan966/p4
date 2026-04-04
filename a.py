from autils import *
from utils import *
from p4 import Trader
import numpy as np
import matplotlib.pyplot as plt

def assert_equal(s1: TradingState, s2: TradingState):
    """Yeah, I know, it looks like minified javascript."""

    if not sorted([(k, t.buyer,t.seller,t.price,t.quantity,t.symbol,t.timestamp) for k, v in s1.market_trades.items() for t in v]) == sorted([(k, t.buyer,t.seller,t.price,t.quantity,t.symbol,t.timestamp) for k, v in s2.market_trades.items() for t in v]):
        sys.exit("1\n" + json.dumps(s1.market_trades, cls=MyP4Encoder) + "\n\n" + json.dumps(s2.market_trades, cls=MyP4Encoder))
    if not sorted(s1.order_depths.items()) == sorted(s2.order_depths.items()):
        sys.exit("2\n" + json.dumps(s1, cls=MyP4Encoder) + "\n\n" + json.dumps(s2, cls=MyP4Encoder))
    if not sorted([(k, t.buyer,t.seller,t.price,t.quantity,t.symbol,t.timestamp) for k, v in s1.own_trades.items() for t in v]) == sorted([(k, t.buyer,t.seller,t.price,t.quantity,t.symbol,t.timestamp) for k, v in s2.own_trades.items() for t in v]):
        sys.exit("3\n" + json.dumps(s1.own_trades, cls=MyP4Encoder) + "\n\n" + json.dumps(s2.own_trades, cls=MyP4Encoder))
    if not sorted([(k, v) for k, v in s1.position.items() if v]) == sorted([(k, v) for k, v in s2.position.items() if v]):
        sys.exit("4\n" + json.dumps(s1, cls=MyP4Encoder) + "\n\n" + json.dumps(s2, cls=MyP4Encoder))
    if not s1.timestamp == s2.timestamp:
        sys.exit("5\n" + json.dumps(s1, cls=MyP4Encoder) + "\n\n" + json.dumps(s2, cls=MyP4Encoder))

def main2():
    bt_states = get_trading_states_from_log("46883")
    # bt_states = get_trading_states_from_data()
    reactions = backtest(Trader(), bt_states, use_local=False, use_reasons=True)
    states = [reaction.input_state for reaction in reactions]

    # tomato_prices = [get_wall_mid(s.order_depths["TOMATOES"]) for s in states]
    # tomato_random_walk = generate_similar_random_walk(np.array(tomato_prices))
    # tomato_random_walk_ma = calculate_moving_average(tomato_random_walk, 20, pad_front=None)
    # delta = np.array(tomato_random_walk)-np.array(tomato_random_walk_ma)
    # print(detect_mean_reversion(delta))
    # plt.plot(delta)

    # plt.savefig("image.png")

    tomato_prices = [get_wall_mid(s.order_depths["TOMATOES"]) for s in states]
    tomato_random_walk = generate_similar_random_walk(np.array(tomato_prices))

    window = 20
    tomato_rw_array = np.array(tomato_random_walk)
    tomato_rw_ma = np.array([np.mean(tomato_rw_array[i-window:i]) for i in range(window, len(tomato_rw_array))])
    delta = tomato_rw_array[window:] - tomato_rw_ma  # both same length, no nans

    print(detect_mean_reversion(delta))
    plt.plot(delta)
    plt.savefig("image.png")

def main():
    bt_states = get_trading_states_from_log("46883")
    # bt_states = get_trading_states_from_data()
    reactions = backtest(Trader(), bt_states, use_local=False, use_reasons=True)
    states = [reaction.input_state for reaction in reactions]

    # for i in range(len(states)):
    #     assert_equal(states[i], bt_states[i])
    pnls = get_pnls_from_reactions(reactions)
    # print(sum(pnls[-1].values()))
    # plt.plot([sum(pnl.values()) for pnl in pnls])

    tomato_prices = [get_wall_mid(s.order_depths["TOMATOES"]) for s in states]
    tomato_prices_ma = calculate_moving_average(tomato_prices, 20, pad_front=None)
    delta = np.array(tomato_prices)-np.array(tomato_prices_ma)
    print(detect_mean_reversion(np.array(tomato_prices)-np.array(tomato_prices_ma)))
    plt.plot(delta)

    plt.savefig("image.png")

# main()
main2()