"""
Backtesting Example
"""

from utils import *
from p4 import Trader

states = get_trading_states_from_log("46883")
# states = [s for s in states if 100000 <= s.timestamp]
print(pretty([s for s in states if [True for p,ts in s.own_trades.items() if len(ts)]][0]))
reactions = backtest(Trader(), states, use_local=True, use_reasons=True)
# print(reactions[-1])
pnls = get_pnls_from_reactions(reactions)
# print(pnls[-1])
print(f"Final Pnl: {sum(pnls[-1].values())}")

import matplotlib.pyplot as plt

plt.title("Backtest Results")
plt.xlabel("Timestamp")
plt.ylabel("Pnl")
plt.plot([sum(pnl.values()) for pnl in pnls], label="total")
# plt.plot([pnl.get("make tomatoes", 0) for pnl in pnls], label="make tomatoes")
# plt.plot([pnl.get("take tomatoes", 0) for pnl in pnls], label="take tomatoes")
# plt.plot([pnl.get("flatten tomatoes", 0) for pnl in pnls], label="flatten tomatoes")
plt.legend()
plt.savefig("image.png")