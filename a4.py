from utils import *
from autils import *
import matplotlib.pyplot as plt
import numpy as np


def detect_autocorrelation(prices, max_lag=50):
    returns = np.diff(prices) / np.array(prices[:-1])
    lags = range(1, max_lag+1)
    acf = [np.corrcoef(returns[:-lag], returns[lag:])[0,1] for lag in lags]
    plt.plot(lags, acf)
    plt.axhline(0, color='red', linestyle='--')
    plt.axhline(1.96/np.sqrt(len(returns)), color='gray', linestyle='--')
    plt.axhline(-1.96/np.sqrt(len(returns)), color='gray', linestyle='--')
    plt.xlabel('lag')
    plt.ylabel('autocorrelation')
    plt.title('Return Autocorrelation')
    plt.savefig("image.png")
    return acf

use_cache = True
states = get_trading_states_from_data("data_p3/round3", [2,3,4], use_p3=True, use_cache=use_cache)

product = "VOLCANIC_ROCK"
mids = [get_wall_mid(s.order_depths[product]) for s in states]
assert None not in mids


detect_autocorrelation(np.array(mids))

# plt.plot(bids, color="blue")
# plt.plot(asks, color="red")
# plt.savefig("image.png")