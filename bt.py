"""
Backtester.
"""

from utils import *
from p4 import Trader

states = get_trading_states_from_data()
pnls, logs = backtest(Trader(), states)
print([p for t, p in sorted(pnls.items())][-1])

import matplotlib.pyplot as plt

plt.title("Backtest Results")
plt.xlabel("Timestamp")
plt.ylabel("Pnl")
plt.plot([p for t, p in sorted(pnls.items())])
plt.savefig("image.png")