import jsonpickle
import json
from typing import NamedTuple
from copy import deepcopy
from collections import defaultdict
from datamodel import TradingState, Order, OrderDepth, Trade
from sortedcontainers import SortedKeyList
import sys
import os
import io
import contextlib

PRODUCTS = ["EMERALDS", "TOMATOES"]

def pretty(obj, indent=0):
    """Usage: print(pretty(stuff))"""

    pad = "  " * indent
    inner = "  " * (indent + 1)

    if hasattr(obj, '_fields'):
        lines = [f"{inner}{f}={pretty(getattr(obj, f), indent + 1)}" for f in obj._fields]
        return f"{type(obj).__name__}(\n" + "\n".join(lines) + f"\n{pad})"

    if isinstance(obj, dict):
        if not obj: return "{}"
        lines = [f"{inner}{k!r}: {pretty(v, indent + 1)}" for k, v in obj.items()]
        return "{\n" + "\n".join(lines) + f"\n{pad}}}"

    if isinstance(obj, (list)):
        if not obj: return repr(obj)
        open_, close = ("[", "]") if isinstance(obj, list) else ("(", ")")
        lines = [f"{inner}{pretty(v, indent + 1)}" for v in obj]
        return open_ + "\n" + "\n".join(lines) + f"\n{pad}" + close

    if hasattr(obj, '__dict__'):
        if not obj.__dict__: return repr(obj)
        lines = [f"{inner}{k}={pretty(v, indent + 1)}" for k, v in obj.__dict__.items()]
        return f"{type(obj).__name__}(\n" + "\n".join(lines) + f"\n{pad})"

    return repr(obj)

def correct_state(state: TradingState):
    """
    Fixes order_depths field in deserialized TradingState object.

    The keys in order_depths, which represents prices, will become strings
    when the bounding TradingState object is pickled then depickled.
    """

    correct_order_depths = {}
    for product, d in state.order_depths.items():
        d1 = OrderDepth()
        d1.buy_orders = {int(p): q for p, q in d.buy_orders.items()}
        d1.sell_orders = {int(p): q for p, q in d.sell_orders.items()}
        correct_order_depths[product] = d1
    
    return TradingState(
        traderData=state.traderData,
        timestamp=state.timestamp,
        listings=state.listings,
        order_depths=correct_order_depths,
        own_trades=state.own_trades,
        market_trades=state.market_trades,
        position=state.position,
        observations=state.observations
    )
    
def get_relevant_state(state: TradingState):
    """
    Remove outdated trades form TradingState object.
    
    state.market_trades and state.own_trades will contain outdated trades
    -- trades that did not happen in the previous timestamp, but long before. 
    This function removes them.
    """

    relevant_own_trades = {}
    for product, trades in state.own_trades.items():
        relevant_own_trades[product] = [t for t in trades if t.timestamp == state.timestamp-100]

    relevant_market_trades = {}
    for product, trades in state.market_trades.items():
        relevant_market_trades[product] = [t for t in trades if t.timestamp == state.timestamp-100]

    return TradingState(
        traderData=state.traderData,
        timestamp=state.timestamp,
        listings=state.listings,
        order_depths=state.order_depths,
        own_trades=relevant_own_trades,
        market_trades=relevant_market_trades,
        position=state.position,
        observations=state.observations
    )

class TraderLog(NamedTuple):
    state: TradingState
    orders: dict[str, list[Order]]

def get_trader_logs(log_id):
    """
    Gets a list of TraderLogs by log id from the logs/ folder.

    Usage: download a testing run in the prosperity dashboard, unzip it, and put the unzipped folder in a folder named "logs". Use the folder name (eg. 33608) as the log_id.
    """

    with open(f"logs/{log_id}/{log_id}.log") as f:
        content = f.read()
        lambda_logs: dict[str, object] = jsonpickle.loads(content) # type: ignore
        raw_logs: list[dict[str, str]] = lambda_logs["logs"] # type: ignore
        print("rejected" in content.lower())
    
    with open(f"logs/{log_id}/{log_id}.json") as f:
        content = f.read()
        print("rejected" in content.lower())


    logs: dict[int, TraderLog] = {}
    for log in raw_logs:
        user_log = log["lambdaLog"]

        if user_log.startswith("[ERROR]"):
            sys.exit(pretty(json.loads(user_log[user_log.index("\\n")+2:])))
        
        try:
            user_log = jsonpickle.loads(user_log) # type: ignore
            state: TradingState = user_log['state'] # type: ignore
            orders: dict[str, list[Order]] = user_log['orders'] # type: ignore

            logs[state.timestamp] = TraderLog(
                state=correct_state(state), 
                orders=orders
            )
        except Exception:
            sys.exit(str(user_log))

    return logs

# fill behavior
# highlight your orders

class Book:
    """Pretty much useless given the new trading model, where the bots submit new orders after your orders get cancelled. Should make a new one to incorporate that."""

    def __init__(self):
        """Creates a book, no arguments needed"""

        self.bid_ps = SortedKeyList([], key=lambda t: -t)
        self.bid_qs = {}
        self.bot_tot_bid_qs = defaultdict(int)
        self.my_tot_bid_qs = defaultdict(int)
        self.my_bid_qs = {}

        self.ask_ps = SortedKeyList([], key=lambda t: t)
        self.ask_qs = {}
        self.bot_tot_ask_qs = defaultdict(int)
        self.my_tot_ask_qs = defaultdict(int)
        self.my_ask_qs = {}

        self.position = 0
    
    def add_bot_trades(self, trades: list[Trade]):
        """Adds provided trades as bot trades to the current book."""
        for t in trades:
            self.bot_tot_bid_qs[t.price] += t.quantity
            self.bot_tot_ask_qs[t.price] -= t.quantity
        
        return deepcopy(self)

    def set_bot_order_depth(self, order_depth: OrderDepth):
        """Sets bot book without affecting my orders. Throws error when a trade is detected."""
        bid_ps = SortedKeyList(set(order_depth.buy_orders.keys()) | set(self.my_bid_qs.keys()), key=lambda t: -t)
        ask_ps = SortedKeyList(set(order_depth.sell_orders.keys()) | set(self.my_ask_qs.keys()), key=lambda t: t)
        if bid_ps[0] >= ask_ps[0]:
            sys.exit(f"Trades detected: order_depth: {({**order_depth.buy_orders, **order_depth.sell_orders})}, my_bid_qs: {self.my_bid_qs}, my_ask_qs: {self.my_ask_qs}")
        qs = {**order_depth.buy_orders, **order_depth.sell_orders}
        self.bid_qs = {}
        self.ask_qs = {}
        for p in bid_ps:
            self.bid_qs[p] = self.my_bid_qs.get(p, 0) + qs.get(p, 0)
        for p in ask_ps:
            self.ask_qs[p] = self.my_ask_qs.get(p, 0) + qs.get(p, 0)
        self.bid_ps = bid_ps
        self.ask_ps = ask_ps

        return deepcopy(self)

    def add_my_trades(self, trades: list[Trade]):
        """Adds my trades to the current book."""

        for t in trades:
            trade_quantity = -t.quantity if t.seller == "SUBMISSION" else t.quantity

            if t.price in self.my_bid_qs: # i bought from the bot
                self.bid_qs[t.price] -= trade_quantity
                self.bot_tot_ask_qs[t.price] -= trade_quantity
                self.my_tot_bid_qs[t.price] += trade_quantity
                self.my_bid_qs[t.price] -= trade_quantity
                self.position += t.price
                if self.my_bid_qs[t.price] < 0:
                    raise Exception("Invalid trades.")
                if self.bid_qs[t.price] < 0:
                    raise Exception("Invalid trades.")
                if self.my_bid_qs[t.price] == 0:
                    del self.my_bid_qs[t.price]
                if self.bid_qs[t.price] == 0:
                    self.bid_ps.remove(t.price)
            if t.price in self.my_ask_qs: # i'm selling
                self.ask_qs[t.price] -= trade_quantity
                self.bot_tot_bid_qs[t.price] -= trade_quantity
                self.my_tot_ask_qs[t.price] += trade_quantity
                self.my_ask_qs[t.price] -= trade_quantity
                self.position += trade_quantity
                if self.my_ask_qs[t.price] > 0:
                    raise Exception("Invalid trades.")
                if self.ask_qs[t.price] > 0:
                    raise Exception("Invalid trades.")
                if self.my_ask_qs[t.price] == 0:
                    del self.my_ask_qs[t.price]
                if self.ask_qs[t.price] == 0:
                    self.ask_ps.remove(t.price)

        return deepcopy(self)
    
    def add_my_orders(self, orders: list[Order], timestamp: int):
        """Adds my orders to the current book."""

        my_trades: list[Trade] = []

        for order in orders:
            q = order.quantity
            while q > 0 and len(self.ask_ps) and self.ask_ps[0] <= order.price: # i'm buying
                p: int = self.ask_ps[0] # type: ignore
                left = q + self.ask_qs[p]
                if left < 0:
                    self.my_tot_bid_qs[p] += q
                    self.position += q
                    my_trades.append(Trade(
                        symbol=order.symbol,
                        price=p,
                        quantity=q,
                        buyer="SUBMISSION",
                        seller="",
                        timestamp=timestamp
                    ))
                    self.ask_qs[p] = left
                    q = 0
                else:
                    self.my_tot_bid_qs[p] -= self.ask_qs[p]
                    self.position -= self.ask_qs[p]
                    my_trades.append(Trade(
                        symbol=order.symbol,
                        price=p,
                        quantity=-self.ask_qs[p],
                        buyer="SUBMISSION",
                        seller="",
                        timestamp=timestamp
                    ))
                    del self.ask_qs[p]
                    self.ask_ps.remove(p)
                    q = left
            
            while q < 0 and len(self.bid_ps) and self.bid_ps[0] >= order.price: # i'm selling
                p: int = self.bid_ps[0] # type: ignore
                left = q + self.bid_qs[p]
                if left > 0:
                    self.my_tot_ask_qs[p] += q
                    self.position += q
                    my_trades.append(Trade(
                        symbol=order.symbol,
                        price=p,
                        quantity=-q,
                        buyer="",
                        seller="SUBMISSION",
                        timestamp=timestamp
                    ))
                    self.bid_qs[p] = left
                    q = 0
                else:
                    self.my_tot_ask_qs[p] -= self.bid_qs[p]
                    self.position -= self.bid_qs[p]
                    my_trades.append(Trade(
                        symbol=order.symbol,
                        price=p,
                        quantity=self.bid_qs[p],
                        buyer="",
                        seller="SUBMISSION",
                        timestamp=timestamp
                    ))
                    del self.bid_qs[p]
                    self.bid_ps.remove(p)
                    q = left

            if q > 0:
                if order.price in self.bid_qs:
                    self.bid_qs[order.price] += q
                else:
                    self.bid_ps.add(order.price)
                    self.bid_qs[order.price] = q
                if order.price in self.my_bid_qs:
                    self.my_bid_qs[order.price] += q
                else:
                    self.my_bid_qs[order.price] = q
            if q < 0:
                if order.price in self.ask_qs:
                    self.ask_qs[order.price] += q
                else:
                    self.ask_ps.add(order.price)
                    self.ask_qs[order.price] = q
                if order.price in self.my_ask_qs:
                    self.my_ask_qs[order.price] += q
                else:
                    self.my_ask_qs[order.price] = q
                
        return deepcopy(self), my_trades
    
    def cancel_my_open_orders(self):
        """Remove my open orders from the book. Throw an error if there is insufficient quantity"""

        # cancelled_orders = []

        for p, q in self.my_bid_qs.items():
            self.bid_qs[p] -= q
            # cancelled_orders.append(T(p, q))
            if self.bid_qs[p] < 0:
                raise Exception("Open orders larger than current orders on book.")
            if self.bid_qs[p] == 0:
                del self.bid_qs[p]
                self.bid_ps.remove(p)
        for p, q in self.my_ask_qs.items():
            self.ask_qs[p] -= q
            # cancelled_orders.append(T(p, q))
            if self.ask_qs[p] > 0:
                raise Exception("Open orders larger than current orders on book.")
            if self.ask_qs[p] == 0:
                del self.ask_qs[p]
                self.ask_ps.remove(p)
        
        self.my_bid_qs.clear()
        self.my_ask_qs.clear()
        
        return deepcopy(self)
        
    def get_bids(self):
        """Returns the bids on book as a list of (price, quantity) tuples."""

        return [(p, self.bid_qs[p]) for p in self.bid_ps]
    
    def get_asks(self):
        """Returns the bids on book as a list of (price, quantity) tuples."""

        return [(p, self.ask_qs[p]) for p in self.ask_ps]

    def __repr__(self):
        """Stringify, shows the orderbook."""

        return str(list(reversed(self.get_bids()))) + " || " + str(self.get_asks())

def get_remaining_orders(product: str, orders: list[Order], trades: list[Trade]):
    """Returns orders - trades."""

    qs = {}
    for order in orders:
        if order.price not in qs:
            qs[order.price] = 0
        qs[order.price] += order.quantity
    for trade in trades:
        qs[trade.price] -= trade.quantity
    return [Order(symbol=product, price=p, quantity=q) for p, q in qs.items() if q != 0]

def get_my_makes(my_trades: list[Trade], my_takes: list[Trade]):
    """Returns my_trades - my_takes."""

    trade_tuples1 = {(trade.buyer, trade.seller, trade.price, trade.quantity, trade.timestamp, trade.symbol) for trade in my_trades}
    trade_tuples2 = {(trade.buyer, trade.seller, trade.price, trade.quantity, trade.timestamp, trade.symbol) for trade in my_takes}
    if not trade_tuples2 <= trade_tuples1:
        sys.exit(f"My trades does not contain my takes: t={my_takes[0].timestamp}\nMy trades: {my_trades}\nMy takes: {my_takes}")
    remaining_trade_tuples = trade_tuples1 - trade_tuples2
    return [Trade(buyer=b, seller=s, price=p, quantity=q, timestamp=t, symbol=sb) for b, s, p, q, t, sb in remaining_trade_tuples]


def wall_mid_formula(order_depth):
    """
    Returns the "fair price".
    
    Interesting phenomenon in these prosperity contests: there will be "walls" (large bids and asks) that define the reasonable trade range. You virtually cannot break through the walls. The average of the wall prices is the "reasonable price"
    """

    return (min(order_depth.buy_orders.keys()) + max(order_depth.sell_orders.keys())) / 2


def print_log_item(log: TraderLog, mid_price_formula=wall_mid_formula, products=PRODUCTS):
    """
    Pretty-prints a TraderLog.
    """

    state = log.state
    print(f" === Trader Log T = {state.timestamp} === ")
    for product in products:
        print(f"{product}:")
        book = state.order_depths.get(product, OrderDepth())
        own_trades = state.own_trades.get(product, [])
        market_trades = state.market_trades.get(product, [])
        position = state.position.get(product, 0)
        orders = log.orders.get(product, [])
        buy_orders = [(p, 0, q) for p, q in book.buy_orders.items()]
        sell_orders = [(p, 0, q) for p, q in book.sell_orders.items()]
        my_orders = [(order.price, -1 if order.quantity > 0 else 1, order.quantity) for order in orders]
        my_trades = [(trade.price, 2, trade.quantity) for trade in own_trades if trade.timestamp == state.timestamp-100]
        bot_trades = [(trade.price, 3, trade.quantity) for trade in market_trades if trade.timestamp == state.timestamp-100]
        mid_price = mid_price_formula(book)
        for order in sorted(buy_orders + sell_orders + my_orders + my_trades + bot_trades + [(mid_price, 4, 0)], reverse=True):
            if order[1] == 0:
                print(f"\t({order[0]}, {order[2]})")
            elif abs(order[1]) == 1:
                print(f"\t<<{order[0]}, {order[2]}>>")
            elif order[1] == 2:
                print(f"\tOWN <<{order[0]}, {order[2]}>>")
            elif order[1] == 3:
                print(f"\tBOT ({order[0]}, {order[2]})")
            else:
                print(f"MID: {order[0]} -------------")
        if position > 0:
            print(f"\tLONG: {position}")
        elif position < 0:
            print(f"\tSHORT: {position}")
        else:
            print(f"\tFLAT POSITION")
        if not my_trades:
            print(f"\tNO OWN TRADES")
        if not bot_trades:
            print(f"\tNO BOT TRADES")
        if not orders:
            print(f"\tNO ORDERS POSTED")

# def get_snapshots(logs: dict[int, TraderLog], product: str):
#     """
#     Returns a list of snapshots for visualization. Pretty much useless. 
    
#     Can also be used to show if bots have traded after your orders are cancelled, which is always true.
#     """

#     # This procedure is separating the trades and pushing them in. 
#     # one potentially superior procedure is to get a list of orders for the bots and a list of orders for the trader and pushing them onto an orderbook
#     timestamp = 0
#     book = Book()
#     my_orders = []
#     my_takes = []
#     snapshots = []
#     while timestamp < 200000:
#         print_log_item(logs[timestamp], wall_mid_formula)

#         # yesterday...
#         bot_trades = [t for t in logs[timestamp].state.market_trades.get(product, []) if t.timestamp == timestamp-100]
#         my_trades = [t for t in logs[timestamp].state.own_trades.get(product, []) if t.timestamp == timestamp-100]
#         my_makes = get_my_makes(my_trades, my_takes)
#         my_standing_orders = get_remaining_orders(product, my_orders, my_trades)

#         # bots trade on me
#         book = book.cancel_my_open_orders()
#         book = book.add_my_trades(my_trades)
#         book, empty_trades = book.add_my_orders(my_standing_orders, timestamp-100)
#         assert len(empty_trades) == 0, "adding my orders creates non-empty trades"

#         # bots trade with each other
#         order_depths = logs[timestamp].state.order_depths[product]
#         book = book.set_bot_order_depth(order_depths)
#         book = book.add_bot_trades(bot_trades)
        
#         # my orders get cancelled
#         book = book.cancel_my_open_orders()

#         # today...
#         my_orders = logs[timestamp].orders.get(product, [])
#         book, my_takes = book.add_my_orders(my_orders, timestamp)


#         # snap!
#         snapshots.append(snapshot(f"{timestamp}", book, trades=my_takes + my_makes, bot_trades=bot_trades))
#         timestamp += 100
#     return snapshots

def capture_prints(function):
    """Pass the function inside this function to run it while having the prints captured."""

    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        result = function()
    prints = f.getvalue()
    return result, prints

def clear_console():
    """
    If you run python something.py in the console, this function removes everything in the console.
    """

    os.system('cls' if os.name == 'nt' else 'clear')