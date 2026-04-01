"""
Backtester.
"""

from utils import *
from p4 import Trader

# TODO: convert logs to TraderLog and fire analysis like plot2.py
pnls, logs = backtest(Trader())
print([p for t, p in sorted(pnls.items())][-1])

import matplotlib.pyplot as plt

plt.title("Backtest Results")
plt.xlabel("Timestamp")
plt.ylabel("Pnl")
plt.plot([p for t, p in sorted(pnls.items())])
plt.savefig("image.png")