import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from utils import *
from p4 import Trader, PARAMETERS

PLOT_ORDERBOOK = False
PLOT_BOT_TRADES = True
def plot_own_trade(trade):
    return True

bt_states = get_trading_states_from_data("data_p4/round1", [0, 1, 2], use_p3=False, use_cache=True)
bt_results = local_backtest(Trader(), bt_states, use_p3=False, parameters=PARAMETERS)
states = [r.input_state for r in bt_results]
pnl = [sum(p.values()) if None not in p.values() else None for p in get_pnls_from_reactions(bt_results)]
# product = "ASH_COATED_OSMIUM"
product = "INTARIAN_PEPPER_ROOT"
own_trades = [(reason,t) for r in bt_results for reason, trades in r.trades.items() for t in trades if t.symbol == product and plot_own_trade(t)]
buy_trades = [(r,t) for r,t in own_trades if t.buyer == "SUBMISSION"]
sell_trades = [(r,t) for r,t in own_trades if t.seller == "SUBMISSION"]
bot_trades = [t for r in bt_results for t in r.input_state.market_trades.get(product, [])]
orders = [(s.timestamp, p,q) for s in states for p,q in {**s.order_depths.get(product, OrderDepth()).buy_orders,**s.order_depths.get(product, OrderDepth()).sell_orders}.items()]
def mid(timestamp):
    return timestamp * 0.001 + 10000
mmable_bids = [(t,p,q) for t,p,q in orders if 0 < p - mid(t) < 5 and q > 0]
mmable_asks = [(t,p,q) for t,p,q in orders if 0 > p - mid(t) > -5 and q < 0]
print(f"Total ask volume: {sum([q for t,p,q in mmable_asks])}")
print(f"Total bid volume: {sum([q for t,p,q in mmable_bids])}")
mmable_orders = sorted(mmable_bids + mmable_asks, key=lambda x: x[0])
cash = 0
position = 0
for t,p,q in mmable_orders:
    cash -= p*q
    position += q
print(f"Max possible Profit from mm: {cash + position * mid(30000_00)}")
