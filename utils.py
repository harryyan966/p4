import jsonpickle
import json
from typing import NamedTuple
from datamodel import TradingState, Order, OrderDepth, Trade, Listing, Observation
import sys
import os
import io
import contextlib
import numpy as np
import pandas as pd
from tqdm import tqdm
from copy import deepcopy

LISTINGS = {
    "EMERALDS": Listing(
        symbol="EMERALDS",
        product="EMERALDS",
        denomination="1"
    ),
    "TOMATOES": Listing(
        symbol="TOMATOES",
        product="TOMATOES",
        denomination="1"
    ),
}

POSITION_LIMITS = {
    "EMERALDS": 80,
    "TOMATOES": 80
}

def load_trading_states_from_data(min_timestamp = 0, max_timestamp = np.inf):
    """
    Loads a list of TradingStates from provided data files.
    """

    # Grab dataframes
    price_dfs: list[pd.DataFrame] = []
    trade_dfs: list[pd.DataFrame] = []
    for day in [0, 1]:
        price = pd.read_csv(f"data/price{day}.csv", sep=";")
        price["timestamp"] = day * 1000000 + price["timestamp"]
        price_dfs.append(price)
    for day in [0, 1]:
        trade = pd.read_csv(f"data/trade{day}.csv", sep=";")
        trade["timestamp"] = day * 1000000 + trade["timestamp"]
        trade_dfs.append(trade)
    prices_df = pd.concat(price_dfs)
    prices_df = prices_df[(prices_df["timestamp"] <= max_timestamp) & (prices_df["timestamp"] >= min_timestamp)]
    trades_df = pd.concat(trade_dfs)
    trades_df = trades_df[(trades_df["timestamp"] <= max_timestamp) & (trades_df["timestamp"] >= min_timestamp)]

    trading_states: list[TradingState] = []

    # Deserialize trades
    all_trades: dict[int, dict[str, list[Trade]]] = {}
    for _, trade in trades_df.iterrows():
        timestamp: int = int(trade.get("timestamp")) # type: ignore
        product: str = trade["symbol"]
        if timestamp not in all_trades:
            all_trades[timestamp] = {}
        if product not in all_trades[timestamp]:
            all_trades[timestamp][product] = []
        buyer = trade.get("buyer", "")
        seller = trade.get("seller", "")

        all_trades[timestamp][product].append(Trade(
            timestamp=trade.get('timestamp'), # type: ignore
            symbol=product, # type: ignore
            price=int(trade.get('price')), # type: ignore
            quantity=int(trade.get('quantity')), # type: ignore
            buyer="" if np.isnan(buyer) else buyer, # type: ignore
            seller="" if np.isnan(seller) else seller # type: ignore
        ))

    def get_buy_orders(row: pd.Series):
        buy_orders = {}
        for number in [1, 2, 3]:
            if np.isnan(row[f"bid_price_{number}"]):
                continue
            price = int(row[f"bid_price_{number}"])
            quantity = int(row[f"bid_volume_{number}"])
            buy_orders[price] = quantity
        return buy_orders

    def get_sell_orders(row: pd.Series):
        sell_orders = {}
        for number in [1, 2, 3]:
            if np.isnan(row[f"ask_price_{number}"]):
                continue
            price = int(row[f"ask_price_{number}"])
            quantity = int(row[f"ask_volume_{number}"])
            sell_orders[price] = -quantity
        return sell_orders

    # Deserialize prices
    for timestamp, rows in tqdm(prices_df.groupby("timestamp"), total=prices_df["timestamp"].nunique(), desc="Generating Trading States"): # type: ignore
        books = {product: rows[rows.get("product", "") == product].iloc[0] for product in LISTINGS.keys()}
        trades_now = all_trades.get(timestamp, {})

        order_depths = {}
        for product, book in books.items():
            order_depth = OrderDepth()
            order_depth.buy_orders = get_buy_orders(book)
            order_depth.sell_orders = get_sell_orders(book)
            order_depths[product] = order_depth
        
        own_trades = {}

        market_trades = {}
        for product, trades in trades_now.items():
            if product not in market_trades:
                market_trades[product] = []
            for trade in trades:
                market_trades[product].append(trade)
        
        position = {}
        
        trading_states.append(TradingState(
            traderData="",
            timestamp=timestamp,
            listings=LISTINGS,
            order_depths=order_depths,
            own_trades=own_trades,
            market_trades=market_trades,
            position=position,
            observations=Observation(plainValueObservations={},conversionObservations={})
        ))
    
    return sorted(trading_states, key=lambda s: s.timestamp)

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

def get_log_strings(log_id) -> dict[int, str]:
    """
    Gets a list of log strings by log id from the logs/ folder.

    Usage: download a testing run in the prosperity dashboard, unzip it, and put the unzipped folder in a folder named "logs". Use the folder name (eg. 33608) as the log_id.
    """

    with open(f"logs/{log_id}/{log_id}.log") as f:
        content = f.read()
        lambda_logs: dict[str, object] = jsonpickle.loads(content) # type: ignore
        raw_logs: list[dict[str, str]] = lambda_logs["logs"] # type: ignore
    
    with open(f"logs/{log_id}/{log_id}.json") as f:
        content = f.read()

    return {int(log["timestamp"]): log["lambdaLog"] for log in raw_logs}

def parse_log_strings(raw_logs: dict[int, str]) -> dict[int, TraderLog]:
    """
    Parses a dict from timestamp to log string into a dict fro timestamp to TraderLog.
    """
    logs: dict[int, TraderLog] = {}
    for _, log in raw_logs.items():
        if log.startswith("[ERROR]"):
            sys.exit(pretty(json.loads(log[log.index("\\n")+2:])))
        
        try:
            log = jsonpickle.loads(log) # type: ignore
            state: TradingState = log['state'] # type: ignore
            orders: dict[str, list[Order]] = log['orders'] # type: ignore

            logs[state.timestamp] = TraderLog(
                state=correct_state(state), 
                orders=orders
            )
        except Exception:
            sys.exit(str(log))

    return logs

def get_wall_mid(order_depth):
    """
    Returns the "fair price".
    
    Interesting phenomenon in these prosperity contests: there will be "walls" (large bids and asks) that define the reasonable trade range. You virtually cannot break through the walls. The average of the wall prices is the "reasonable price"
    """

    return (min(order_depth.buy_orders.keys()) + max(order_depth.sell_orders.keys())) / 2

def print_trader_log(log: TraderLog, mid_price_formula=get_wall_mid, products=list(LISTINGS.keys())):
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

import heapq

# TODO: implement time order
class Quote(NamedTuple):
    by: str
    price: int
    quantity: int

class Match(NamedTuple):
    buy: Quote
    sell: Quote

class QuoteHeap:
    def __init__(self, bids_heap: bool): 
        self.bids_heap = bids_heap
        self.heap = []
        self.total_size = 0

    def push(self, quote: Quote):
        price_order = -quote.price if self.bids_heap else quote.price
        heapq.heappush(self.heap, (price_order, quote))
        self.total_size += abs(quote.quantity)

    def top(self):
        return self.heap[0][-1]
    
    def pop(self) -> Quote:
        quote = heapq.heappop(self.heap)[-1]
        self.total_size -= abs(quote.quantity)
        return quote
    
    def __bool__(self):
        return bool(self.heap)

class OrderBook:
    def __init__(self):
        self.buys = QuoteHeap(bids_heap=True)
        self.sells = QuoteHeap(bids_heap=False)

    def quote(self, quote: Quote) -> list[Match]:
        matches: list[Match] = []

        by, p, q = quote.by, quote.price, quote.quantity

        while q > 0: # buying
            if not self.sells:
                self.buys.push(Quote(by, p, q)) # add buy order directly and end
                break
            quote_by, ap, aq = self.sells.top() # best ask
            if ap > p: # best ask higher than our bid
                self.buys.push(Quote(by, p, q)) # bid directly
                break
            if aq+q < 0: # best ask can absorb our bid
                self.sells.pop()
                self.sells.push(Quote(quote_by, ap, aq+q))
                matches.append(Match(Quote(by, ap, q), Quote(quote_by, ap, -q)))
                q = 0
            else: # best ask falls
                self.sells.pop()
                matches.append(Match(Quote(by, ap, -aq), Quote(quote_by, ap, aq)))
                q += aq
        while q < 0: # selling
            if not self.buys:
                self.sells.push(Quote(by, p, q)) # add sell order directly and stop
                break
            quote_by, bp, bq = self.buys.top() # best bid
            if bp < p: # best bid lower than our selling price
                self.sells.push(Quote(by, p, q)) # add sell order directly and stop
                break
            if bq+q > 0: # best bid can absorb our order
                self.buys.pop()
                self.buys.push(Quote(quote_by, bp, bq+q))
                matches.append(Match(Quote(quote_by, bp, -q), Quote(by, bp, q)))
                q = 0
            else: # best bid falls
                self.buys.pop()
                matches.append(Match(Quote(quote_by, bp, bq), Quote(by, bp, -bq)))
                q += bq

        return matches

    def quote_without_matching(self, quote: Quote) -> None:
        if quote.quantity > 0:
            self.buys.push(quote)
        if quote.quantity < 0:
            self.sells.push(quote)
        
class Simulation:
    def __init__(self, state: TradingState):
        self.state = state
        self.books: dict[str, OrderBook] = {}
        for product in LISTINGS.keys():
            book = OrderBook()
            order_depth = self.state.order_depths.get(product, OrderDepth())
            bids = order_depth.buy_orders
            asks = order_depth.sell_orders
            for p, q in bids.items():
                filled = book.quote(Quote("", p, q))
                assert len(filled) == 0
            for p, q in asks.items():
                filled = book.quote(Quote("", p, q))
                assert len(filled) == 0
            self.books[product] = book
    
    def fill(self, order: Order, by: str):
        matches = self.books[order.symbol].quote(Quote(by, order.price, order.quantity))
        return [Trade(
            symbol=order.symbol,
            price=match.buy.price,
            quantity=match.buy.quantity,
            buyer=match.buy.by,
            seller=match.sell.by,
            timestamp=self.state.timestamp
        ) for match in matches]

def get_trading_states_from_data(min_t = 0, max_t = 9000000):
    try:
        with open(f"cache/data_trading_states{min_t}-{max_t}.cache") as f:
            trading_states: list[TradingState] = [correct_state(s) for s in jsonpickle.loads(f.read())] # type: ignore
        return trading_states
    except FileNotFoundError:
        trading_states: list[TradingState] = [get_relevant_state(s) for s in load_trading_states_from_data(min_t, max_t)]
        with open(f"cache/data_trading_states{min_t}-{max_t}.cache", "w") as f:
            f.write(jsonpickle.dumps(trading_states)) # type: ignore
        return trading_states

def get_trading_states_from_log(log_id):
    logs = parse_log_strings(get_log_strings(log_id))
    return [get_relevant_state(log.state) for log in logs.values()]

def get_trading_states_from_cache(cache_file):
    with open(f"cache/{cache_file}.cache") as f:
        trading_states: list[TradingState] = [correct_state(s) for s in jsonpickle.loads(f.read())] # type: ignore
    return trading_states

def backtest(trader, trading_states: list[TradingState]) -> tuple[dict[str, dict[int, int]], dict[int, TraderLog]]:
    """
    Backtests a trader.

    TODO: support conversions in backtester.
    """

    pnls = {p: {} for p in LISTINGS.keys()}
    all_logs = {}

    if not trading_states:
        return pnls, all_logs

    cash = {p: 0 for p in LISTINGS.keys()}
    state = trading_states[0]
    for i in tqdm(range(0, len(trading_states)), desc="Running Backtest"):
        is_last_day = i+1 == len(trading_states)

        # Start Simulation And Add Initial Bot Orders
        sim = Simulation(state)
        all_trades: list[Trade] = []

        # Generate And Push Own Orders
        (all_orders, _, traderData), logs = capture_prints(lambda: trader.run(state))
        all_logs[state.timestamp] = logs
        for product, orders in all_orders.items():
            for order in orders:
                all_trades += sim.fill(order, "SUBMISSION")
        
        # Push Market Trades As Orders
        next_market_trades = {} if is_last_day else deepcopy(trading_states[i+1].market_trades)
        for product, market_trades in next_market_trades.items():
            for market_trade in market_trades:
                all_trades += sim.fill(Order(symbol=product, price=market_trade.price, quantity=market_trade.quantity), market_trade.buyer)
                all_trades += sim.fill(Order(symbol=product, price=market_trade.price, quantity=-market_trade.quantity), market_trade.seller)

        # Calculate Own Trades and Market Trades
        own_trades = {product: [] for product in LISTINGS.keys()}
        market_trades = {product: [] for product in LISTINGS.keys()}
        positions = {product: state.position.get(product, 0) for product in LISTINGS.keys()}
        for trade in all_trades:
            product = trade.symbol
            if trade.buyer == "SUBMISSION":
                own_trades[product].append(trade)
                positions[product] += trade.quantity
                cash[product] -= trade.price * trade.quantity
            elif trade.seller == "SUBMISSION":
                own_trades[product].append(trade)
                positions[product] -= trade.quantity
                cash[product] += trade.price * trade.quantity
            else:
                market_trades[product].append(trade)
        
        # Calculate Per-Product Pnls
        for product in LISTINGS.keys():
            position = positions.get(product, 0)
            if abs(position) > POSITION_LIMITS[product]:
                sys.exit(f"Position Exceeded Limits at {state.timestamp} for {product}: {position}")
            product_value = get_wall_mid(state.order_depths[product])
            pnls[product][state.timestamp] = cash[product] + product_value * position

        # Generate Next State
        if not is_last_day:
            state = TradingState(
                traderData=traderData,
                timestamp=trading_states[i+1].timestamp,
                listings=LISTINGS,
                order_depths=trading_states[i+1].order_depths,
                own_trades=own_trades,
                market_trades=market_trades,
                position=positions,
                observations=Observation(plainValueObservations={}, conversionObservations={})
            )
    
    # Parse Logs and Return
    all_logs = parse_log_strings(all_logs)
    return pnls, all_logs

def get_pnls_from_trading_states(states: list[TradingState]):
    pnls = {p: {} for p in LISTINGS.keys()}
    cash = {p: 0 for p in LISTINGS.keys()}
    positions = {p: 0 for p in LISTINGS.keys()}
    for state in states:
        # Update Positions
        for product, trades in state.own_trades.items():
            for trade in trades:
                multiplier = 1 if trade.buyer == "SUBMISSION" else -1
                positions[product] += trade.quantity * multiplier
                cash[product] -= trade.price * trade.quantity * multiplier
        
        # Calculate Pnl
        for product in LISTINGS.keys():
            position = positions.get(product, 0)
            if abs(position) > POSITION_LIMITS[product]:
                sys.exit(f"Position Exceeded Limits at {state.timestamp} for {product}: {position}")
            product_value = get_wall_mid(state.order_depths[product])
            pnls[product][state.timestamp] = cash[product] + product_value * position
    
    return pnls
