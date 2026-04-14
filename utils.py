import json

from typing import NamedTuple, Callable, Any
from datamodel import TradingState, Order, OrderDepth, Trade, Listing, Observation, ConversionObservation
import sys
import os
import io
import contextlib
import numpy as np
import pandas as pd
from tqdm import tqdm
from copy import deepcopy
from collections import deque
import itertools
import os
import heapq
from p4 import P4_POSITION_LIMITS

# P4_LISTINGS = {
#     "EMERALDS": Listing(
#         symbol="EMERALDS",
#         product="EMERALDS",
#         denomination="1"
#     ),
#     "TOMATOES": Listing(
#         symbol="TOMATOES",
#         product="TOMATOES",
#         denomination="1"
#     ),
# }

P4_LISTINGS = {k: Listing(k, k, "1") for k in P4_POSITION_LIMITS.keys()}


P3_POSITION_LIMITS = {
    "RAINFOREST_RESIN": 50,
    "KELP": 50,
    "SQUID_INK": 50,
    "CROISSANTS": 250,
    "JAMS": 350,
    "DJEMBES": 60,
    "PICNIC_BASKET1": 60,
    "PICNIC_BASKET2": 100,
    "VOLCANIC_ROCK": 400,
    "VOLCANIC_ROCK_VOUCHER_9500": 200,
    "VOLCANIC_ROCK_VOUCHER_9750": 200,
    "VOLCANIC_ROCK_VOUCHER_10000": 200,
    "VOLCANIC_ROCK_VOUCHER_10250": 200,
    "VOLCANIC_ROCK_VOUCHER_10500": 200,
    "MAGNIFICENT_MACARONS": 75,
}

P3_LISTINGS = {k: Listing(k, k, "1") for k in P3_POSITION_LIMITS.keys()}

GLOBAL_MAX_TIMESTAMP = 9_000_000

def load_trading_states_from_data(data_loc, days, base_listings, min_timestamp = 0, max_timestamp = GLOBAL_MAX_TIMESTAMP) -> list[TradingState]:
    """
    Loads a list of TradingStates from provided data files.
    """

    # Grab dataframes
    price_dfs: list[pd.DataFrame] = []
    trade_dfs: list[pd.DataFrame] = []
    for day in days:
        prices_path = os.path.normpath(f"{data_loc}/prices{day}.csv")
        trades_path = os.path.normpath(f"{data_loc}/trades{day}.csv")
        price = pd.read_csv(prices_path, sep=";")
        trade = pd.read_csv(trades_path, sep=";")
        price["timestamp"] = day * 1000000 + price["timestamp"]
        trade["timestamp"] = day * 1000000 + trade["timestamp"]
        price_dfs.append(price)
        trade_dfs.append(trade)
    prices_df = pd.concat(price_dfs)
    trades_df = pd.concat(trade_dfs)
    prices_df = prices_df[(prices_df["timestamp"] <= max_timestamp) & (prices_df["timestamp"] >= min_timestamp)]
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
        buyer = "" if np.isnan(trade.get("buyer", "")) else trade.get("buyer", "")
        seller = "" if np.isnan(trade.get("seller", "")) else trade.get("seller", "")

        all_trades[timestamp][product].append(Trade(
            timestamp=trade.get('timestamp'), # type: ignore
            symbol=product, # type: ignore
            price=int(trade.get('price')), # type: ignore
            quantity=int(trade.get('quantity')), # type: ignore
            buyer=buyer, # type: ignore
            seller=seller # type: ignore
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
    products = prices_df["product"].unique()
    listings = {k: v for k, v in base_listings.items() if k in products}
    for timestamp, rows in tqdm(prices_df.groupby("timestamp"), total=prices_df["timestamp"].nunique(), desc="Generating Trading States"): # type: ignore
        books = {row.get("product", ""): row for _, row in rows.iterrows()}
        trades_now = all_trades.get(timestamp-100, {})

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
            listings=listings,
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
        lambda_logs: dict[str, object] = json.loads(content)
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
            log = json.loads(log, cls=MyP4Decoder)
            state: TradingState = log['state']
            orders: dict[str, list[Order]] = log['orders']

            logs[state.timestamp] = TraderLog(
                state=correct_state(state), 
                orders=orders
            )
        except Exception:
            sys.exit(f"Error Parsing log: {log}")

    return logs

def get_best_bid(order_depth: OrderDepth) -> int|None:
    return max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None

def get_best_ask(order_depth: OrderDepth) -> int|None:
    return min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None

def get_bid_wall(order_depth: OrderDepth) -> int|None:
    return min(order_depth.buy_orders.keys()) if order_depth.buy_orders else None

def get_ask_wall(order_depth: OrderDepth) -> int|None:
    return max(order_depth.sell_orders.keys()) if order_depth.sell_orders else None

def get_wall_mid(order_depth: OrderDepth) -> int|None:
    """
    Returns the "fair price".
    Interesting phenomenon in these prosperity contests: there will be "walls" (large bids and asks) that define the reasonable trade range. You virtually cannot break through the walls. The average of the wall prices is the "reasonable price"
    """
    bid_wall = get_bid_wall(order_depth)
    ask_wall = get_ask_wall(order_depth)
    if bid_wall is not None and ask_wall is None:
        return bid_wall
    elif bid_wall is None and ask_wall is not None:
        return ask_wall
    elif bid_wall is None and ask_wall is None:
        return None
    else:
        return (bid_wall + ask_wall) / 2 # type: ignore
    
def get_strict_wall_mid(order_depth: OrderDepth) -> int|None:
    """
    Returns the "fair price".
    Interesting phenomenon in these prosperity contests: there will be "walls" (large bids and asks) that define the reasonable trade range. You virtually cannot break through the walls. The average of the wall prices is the "reasonable price"
    """
    bid_wall = get_bid_wall(order_depth)
    ask_wall = get_ask_wall(order_depth)
    if bid_wall is not None and ask_wall is not None:
        return (bid_wall + ask_wall) / 2 # type: ignore
    return None

def capture_prints(function):
    """Pass the function inside this function to run it while having the prints captured."""

    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        result = function()
    prints = f.getvalue()
    return result, prints

# TODO: implement time order
class Quote(NamedTuple):
    by: str
    price: int
    quantity: int
    reason: str

class Match(NamedTuple):
    buy: Quote
    sell: Quote

    def to_trade(self, symbol: str, timestamp: int):
        return Trade(
            symbol=symbol,
            price=self.buy.price,
            quantity=self.buy.quantity,
            buyer=self.buy.by,
            seller=self.sell.by,
            timestamp=timestamp
        )

class QuoteHeap:
    def __init__(self, bids_heap: bool): 
        self.bids_heap = bids_heap
        self.heap = []
        self.total_size = 0
        self.counter = 0

    def push(self, quote: Quote):
        price_order = -quote.price if self.bids_heap else quote.price
        heapq.heappush(self.heap, (price_order, self.counter, quote))
        self.counter += 1
        self.total_size += abs(quote.quantity)
    
    def replace_top(self, quote: Quote):
        price_order, counter, old_quote = heapq.heappop(self.heap)
        self.total_size -= abs(old_quote.quantity)
        heapq.heappush(self.heap, (price_order, counter, quote))
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

        by, p, q, r = quote.by, quote.price, quote.quantity, quote.reason

        while q > 0: # buying
            if not self.sells:
                self.buys.push(Quote(by, p, q, r)) # add buy order directly and end
                break
            quote_by, ap, aq, ar = self.sells.top() # best ask
            if ap > p: # best ask higher than our bid
                self.buys.push(Quote(by, p, q, r)) # bid directly
                break
            if aq+q < 0: # best ask can absorb our bid
                self.sells.replace_top(Quote(quote_by, ap, aq+q, ar))
                matches.append(Match(Quote(by, ap, q, r), Quote(quote_by, ap, -q, ar)))
                q = 0
            else: # best ask falls
                self.sells.pop()
                matches.append(Match(Quote(by, ap, -aq, r), Quote(quote_by, ap, aq, ar)))
                q += aq
        while q < 0: # selling
            if not self.buys:
                self.sells.push(Quote(by, p, q, r)) # add sell order directly and stop
                break
            quote_by, bp, bq, br = self.buys.top() # best bid
            if bp < p: # best bid lower than our selling price
                self.sells.push(Quote(by, p, q, r)) # add sell order directly and stop
                break
            if bq+q > 0: # best bid can absorb our order
                self.buys.replace_top(Quote(quote_by, bp, bq+q, br))
                matches.append(Match(Quote(quote_by, bp, -q, br), Quote(by, bp, q, r)))
                q = 0
            else: # best bid falls
                self.buys.pop()
                matches.append(Match(Quote(quote_by, bp, bq, br), Quote(by, bp, -bq, r)))
                q += bq

        return matches

    def quote_without_matching(self, quote: Quote) -> None:
        if quote.quantity > 0:
            self.buys.push(quote)
        if quote.quantity < 0:
            self.sells.push(quote)
        
class Simulation:
    def __init__(self, state: TradingState):
        self.books: dict[str, OrderBook] = {}
        for product in state.listings.keys():
            book = OrderBook()
            order_depth = state.order_depths.get(product, OrderDepth())
            bids = order_depth.buy_orders
            asks = order_depth.sell_orders
            for p, q in bids.items():
                filled = book.quote(Quote("", p, q, ""))
                assert len(filled) == 0
            for p, q in asks.items():
                filled = book.quote(Quote("", p, q, ""))
                assert len(filled) == 0
            self.books[product] = book
    
    def fill(self, order: Order, by: str, reason: str):
        return self.books[order.symbol].quote(Quote(by, order.price, order.quantity, reason))

def get_trading_states_from_data(data_loc, days, use_p3=False, min_t=0, max_t=GLOBAL_MAX_TIMESTAMP, use_cache=True):
    base_listings = P3_LISTINGS if use_p3 else P4_LISTINGS
    if use_cache:
        try:
            cache_path = os.path.normpath(f"cache/{data_loc}/states_{days}_{min_t}-{max_t}.cache")
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path) as f:
                trading_states: list[TradingState] = [correct_state(s) for s in json.loads(f.read(), cls=MyP4Decoder)] # type: ignore
            return trading_states
        except FileNotFoundError:
            pass
    trading_states: list[TradingState] = [get_relevant_state(s) for s in load_trading_states_from_data(data_loc, days, base_listings, min_t, max_t)]
    cache_path = os.path.normpath(f"cache/{data_loc}/states_{days}_{min_t}-{max_t}.cache")
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        f.write(json.dumps(trading_states, cls=MyP4Encoder)) # type: ignore
    return trading_states

def get_trading_states_from_log(log_id, min_t = 0, max_t = GLOBAL_MAX_TIMESTAMP):
    try:
        with open(f"cache/log_{log_id}_states{min_t}-{max_t}.cache") as f:
            trading_states: list[TradingState] = [correct_state(s) for s in json.loads(f.read(), cls=MyP4Decoder)] # type: ignore
        return trading_states
    except FileNotFoundError:
        states = sorted([l.state for l in parse_log_strings(get_log_strings(log_id)).values()], key=lambda s: s.timestamp)
        trading_states: list[TradingState] = [get_relevant_state(s) for s in states]
        with open(f"cache/log_{log_id}_states{min_t}-{max_t}.cache", "w") as f:
            f.write(json.dumps(trading_states, cls=MyP4Encoder)) # type: ignore
        return trading_states

class Reaction(NamedTuple):
    input_state: TradingState # state seen by trader
    logs: Any # log string output by trader
    orders: dict[str, list[Order]] # map from reason to order
    trades: dict[str, list[Trade]] # map from reason to trade

class MyP4Encoder(json.JSONEncoder):
    def default(self, o):
        d = o.__dict__.copy()
        d["__type__"] = o.__class__.__name__  # embed the type
        return d

class MyP4Decoder(json.JSONDecoder):
    def __init__(self):
        super().__init__(object_hook=self.decode_object)
    
    def decode_object(self, d):
        t = d.get("__type__")
        if t == "ConversionObservation":
            return ConversionObservation(d["bidPrice"], d["askPrice"], d["transportFees"], d["exportTariff"], d["importTariff"], d["sunlight"], d["humidity"])
        if t == "Listing":
            return Listing(d["symbol"], d["product"], d["denomination"])
        if t == "Order":
            return Order(d["symbol"], d["price"], d["quantity"])
        if t == "Trade":
            return Trade(d["symbol"], d["price"], d["quantity"], d["buyer"], d["seller"], d["timestamp"])
        if t == "OrderDepth":
            depth = OrderDepth()
            depth.buy_orders = {int(k): v for k, v in d["buy_orders"].items()}
            depth.sell_orders = {int(k): v for k, v in d["sell_orders"].items()}
            return depth
        if t == "Observation":
            return Observation(d["plainValueObservations"], d["conversionObservations"])
        if t == "TradingState":
            return TradingState(d["traderData"], d["timestamp"], d["listings"], d["order_depths"], d["own_trades"], d["market_trades"], d["position"], d["observations"])
        return d

def local_backtest(trader, trading_states: list[TradingState], use_p3=False, parameters={}, show_progress=True) -> list[Reaction]:
    """
    Backtests a trader, outputs a list of {state, log: runner_name -> log, trades: reason -> trades}
    TODO: support conversions.
    """
    reactions = []
    if not trading_states:
        return reactions
    state = trading_states[0]
    traderdata = {}
    for i in tqdm(range(0, len(trading_states)), desc="Running Backtest") if show_progress else range(0, len(trading_states)):
        is_last_day = i+1 == len(trading_states)
        sim = Simulation(state)
        trades_by_reason = {}
        own_trades = {}
        market_trades = {}
        positions = {product: state.position.get(product, 0) for product in state.listings.keys()}
        orders, _, traderdata, logs = trader.local_run(state, traderdata, parameters)   
        for reason, orders in orders.items():
            for order in orders:
                for match in sim.fill(order, "SUBMISSION", reason):
                    trade = match.to_trade(order.symbol, state.timestamp)
                    if reason not in trades_by_reason:
                        trades_by_reason[reason] = []
                    trades_by_reason[reason].append(trade)
                    if order.symbol not in own_trades:
                        own_trades[order.symbol] = []
                    own_trades[order.symbol].append(trade)
                    direction = 1 if trade.buyer == "SUBMISSION" else -1
                    positions[order.symbol] += trade.quantity * direction
        # Get Bot Orders Required for the Own Trades To Happen
        # (see which own_trades were not present in the order_depths)
        original_buy_orders: dict[str, dict[int, int]] = {}
        original_sell_orders: dict[str, dict[int, int]] = {}
        bot_orders: list[tuple[Order, str]] = [] # orders and buyers
        next_own_trades = {} if is_last_day else trading_states[i+1].own_trades
        for product, trades in next_own_trades.items():
            for trade in trades:
                if trade.buyer == "SUBMISSION": # I bought, bot sold
                    if product not in original_sell_orders:
                        original_sell_orders[product] = {k:v for k,v in state.order_depths[product].sell_orders.items()}
                    if trade.price not in original_sell_orders[product]:
                        bot_orders.append((Order(
                            symbol=trade.symbol,
                            price=trade.price,
                            quantity=-trade.quantity
                        ), trade.seller))
                    elif original_sell_orders[product][trade.price] + trade.quantity < 0:
                        original_sell_orders[product][trade.price] += trade.quantity
                    elif original_sell_orders[product][trade.price] + trade.quantity == 0:
                        del original_sell_orders[product][trade.price]
                    else:
                        bot_orders.append((Order(
                            symbol=trade.symbol,
                            price=trade.price,
                            quantity=-(trade.quantity+original_sell_orders[product][trade.price])
                        ), trade.seller))
                        del original_sell_orders[product][trade.price]
                elif trade.seller == "SUBMISSION": # I sold, bot bought
                    if product not in original_buy_orders:
                        original_buy_orders[product] = {k:v for k,v in state.order_depths[product].buy_orders.items()}
                    if trade.price not in original_buy_orders[product]:
                        bot_orders.append((Order(
                            symbol=trade.symbol,
                            price=trade.price,
                            quantity=trade.quantity
                        ), trade.buyer))
                    elif original_buy_orders[product][trade.price] - trade.quantity > 0:
                        original_buy_orders[product][trade.price] -= trade.quantity
                    elif original_buy_orders[product][trade.price] - trade.quantity == 0:
                        del original_buy_orders[product][trade.price]
                    else:
                        bot_orders.append((Order(
                            symbol=trade.symbol,
                            price=trade.price,
                            quantity=trade.quantity-original_buy_orders[product][trade.price]
                        ), trade.buyer))
                        del original_buy_orders[product][trade.price]
        # Get Bot Orders Required for Market Trades To Happen
        next_market_trades = {} if is_last_day else trading_states[i+1].market_trades
        for product, trades in next_market_trades.items():
            for trade in trades:
                # Break Each Trade Into Two Orders
                bot_orders.append((Order(symbol=product, price=trade.price, quantity=trade.quantity), trade.buyer))
                bot_orders.append((Order(symbol=product, price=trade.price, quantity=-trade.quantity), trade.seller))
        # Push Bot Trades
        for order, by in bot_orders:
            for match in sim.fill(order, by, ""):
                product = order.symbol
                trade = match.to_trade(product, state.timestamp)
                if match.buy.by == "SUBMISSION":
                    if match.buy.reason not in trades_by_reason:
                        trades_by_reason[match.buy.reason] = []
                    trades_by_reason[match.buy.reason].append(trade)
                    if product not in own_trades:
                        own_trades[product] = []
                    own_trades[product].append(trade)
                    positions[product] += trade.quantity
                elif match.sell.by == "SUBMISSION":
                    if match.sell.reason not in trades_by_reason:
                        trades_by_reason[match.sell.reason] = []
                    trades_by_reason[match.sell.reason].append(trade)
                    if product not in own_trades:
                        own_trades[product] = []
                    own_trades[product].append(trade)
                    positions[product] -= trade.quantity
                else:
                    if product not in market_trades:
                        market_trades[product] = []
                    market_trades[product].append(trade)
        # Enforce Position Limits
        position_limits = P3_POSITION_LIMITS if use_p3 else P4_POSITION_LIMITS
        for product in state.listings.keys():
            position = positions.get(product, 0)
            if abs(position) > position_limits[product]:
                sys.exit(f"Position Exceeded Limits at {state.timestamp} for {product}: {position}")
        # Push Results
        reactions.append(Reaction(
            input_state=state,
            logs=logs,
            orders=orders,
            trades=trades_by_reason,
        ))
        # Generate Next State
        if not is_last_day:
            state = TradingState(
                traderData="",
                timestamp=trading_states[i+1].timestamp,
                listings=state.listings,
                order_depths=trading_states[i+1].order_depths,
                own_trades=own_trades,
                market_trades=market_trades,
                position=positions,
                observations=Observation(plainValueObservations={}, conversionObservations={})
            )
    return reactions

def real_backtest(trader, trading_states: list[TradingState], use_p3=False, parameters={}, show_progress=True) -> list[Reaction]:
    """
    Backtests a trader, outputs a list of {state, logs: runner_name -> log, trades: reason -> trades}
    TODO: support conversions.
    """
    reactions = []
    if not trading_states:
        return reactions
    state = trading_states[0]
    traderdata = ""
    for i in tqdm(range(0, len(trading_states)), desc="Running Backtest") if show_progress else range(0, len(trading_states)):
        is_last_day = i+1 == len(trading_states)
        sim = Simulation(state)
        own_trades = {}
        market_trades = {}
        positions = {product: state.position.get(product, 0) for product in state.listings.keys()}
        (orders, _, traderdata), logs = capture_prints(lambda: trader.run(state))
        for product, orders in orders.items():
            for order in orders:
                for match in sim.fill(order, "SUBMISSION", product):
                    trade = match.to_trade(order.symbol, state.timestamp)
                    if order.symbol not in own_trades:
                        own_trades[order.symbol] = []
                    own_trades[order.symbol].append(trade)
                    direction = 1 if trade.buyer == "SUBMISSION" else -1
                    positions[order.symbol] += trade.quantity * direction
        # Get Bot Orders Required for the Own Trades To Happen
        # (see which own_trades were not present in the order_depths)
        original_buy_orders: dict[str, dict[int, int]] = {}
        original_sell_orders: dict[str, dict[int, int]] = {}
        bot_orders: list[tuple[Order, str]] = [] # orders and buyers
        next_own_trades = {} if is_last_day else trading_states[i+1].own_trades
        for product, trades in next_own_trades.items():
            for trade in trades:
                if trade.buyer == "SUBMISSION": # I bought, bot sold
                    if product not in original_sell_orders:
                        original_sell_orders[product] = {k:v for k,v in state.order_depths[product].sell_orders.items()}
                    if trade.price not in original_sell_orders[product]:
                        bot_orders.append((Order(
                            symbol=trade.symbol,
                            price=trade.price,
                            quantity=-trade.quantity
                        ), trade.seller))
                    elif original_sell_orders[product][trade.price] + trade.quantity < 0:
                        original_sell_orders[product][trade.price] += trade.quantity
                    elif original_sell_orders[product][trade.price] + trade.quantity == 0:
                        del original_sell_orders[product][trade.price]
                    else:
                        bot_orders.append((Order(
                            symbol=trade.symbol,
                            price=trade.price,
                            quantity=-(trade.quantity+original_sell_orders[product][trade.price])
                        ), trade.seller))
                        del original_sell_orders[product][trade.price]
                elif trade.seller == "SUBMISSION": # I sold, bot bought
                    if product not in original_buy_orders:
                        original_buy_orders[product] = {k:v for k,v in state.order_depths[product].buy_orders.items()}
                    if trade.price not in original_buy_orders[product]:
                        bot_orders.append((Order(
                            symbol=trade.symbol,
                            price=trade.price,
                            quantity=trade.quantity
                        ), trade.buyer))
                    elif original_buy_orders[product][trade.price] - trade.quantity > 0:
                        original_buy_orders[product][trade.price] -= trade.quantity
                    elif original_buy_orders[product][trade.price] - trade.quantity == 0:
                        del original_buy_orders[product][trade.price]
                    else:
                        bot_orders.append((Order(
                            symbol=trade.symbol,
                            price=trade.price,
                            quantity=trade.quantity-original_buy_orders[product][trade.price]
                        ), trade.buyer))
                        del original_buy_orders[product][trade.price]
        # Get Bot Orders Required for Market Trades To Happen
        next_market_trades = {} if is_last_day else trading_states[i+1].market_trades
        for product, trades in next_market_trades.items():
            for trade in trades:
                # Break Each Trade Into Two Orders
                bot_orders.append((Order(symbol=product, price=trade.price, quantity=trade.quantity), trade.buyer))
                bot_orders.append((Order(symbol=product, price=trade.price, quantity=-trade.quantity), trade.seller))
        # Push Bot Trades
        for order, by in bot_orders:
            for match in sim.fill(order, by, ""):
                product = order.symbol
                trade = match.to_trade(product, state.timestamp)
                if match.buy.by == "SUBMISSION":
                    if product not in own_trades:
                        own_trades[product] = []
                    own_trades[product].append(trade)
                    positions[product] += trade.quantity
                elif match.sell.by == "SUBMISSION":
                    if product not in own_trades:
                        own_trades[product] = []
                    own_trades[product].append(trade)
                    positions[product] -= trade.quantity
                else:
                    if product not in market_trades:
                        market_trades[product] = []
                    market_trades[product].append(trade)
        # Enforce Position Limits
        position_limits = P3_POSITION_LIMITS if use_p3 else P4_POSITION_LIMITS
        for product in state.listings.keys():
            position = positions.get(product, 0)
            if abs(position) > position_limits[product]:
                sys.exit(f"Position Exceeded Limits at {state.timestamp} for {product}: {position}")
        # Push Results
        reactions.append(Reaction(
            input_state=state,
            logs=logs,
            orders=orders,
            trades=own_trades,
        ))
        # Generate Next State
        if not is_last_day:
            state = TradingState(
                traderData=traderdata,
                timestamp=trading_states[i+1].timestamp,
                listings=state.listings,
                order_depths=trading_states[i+1].order_depths,
                own_trades=own_trades,
                market_trades=market_trades,
                position=positions,
                observations=Observation(plainValueObservations={}, conversionObservations={})
            )
    return reactions

class PnlAccount:
    def __init__(self):
        self.cash = 0
        self.positions = {}

    def trade(self, product, price, quantity):
        if product not in self.positions:
            self.positions[product] = 0
        self.positions[product] += quantity
        self.cash -= price * quantity
    
    def get_pnl(self, product_values):
        if None in product_values.values():
            return None
        positions_value = sum([position * product_values[product] for product, position in self.positions.items()])
        return self.cash + positions_value

def get_final_pnl_from_trading_states(states: list[TradingState]):
    """DEPRECATED"""

    sim = PnlAccount()
    for state in states:
        # Update Positions
        for product, trades in state.own_trades.items():
            for trade in trades:
                multiplier = 1 if trade.buyer == "SUBMISSION" else -1
                sim.trade(product, trade.price, trade.quantity * multiplier)
        
        # Calculate Pnl
    fair_prices = {get_wall_mid(states[-1].order_depths[product]) for product in sim.positions.keys()}
    return sim.get_pnl(fair_prices)

def get_pnls_from_reactions(reactions: list[Reaction]) -> list[dict[str, int]]:
    """
    Returns a list of a dictionary that maps reason of trade to cumulative pnl.

    Assumes the reactions are sorted by timestamp.
    """

    sims: dict[str, PnlAccount] = {}
    pnls: list[dict[str, int]] = []
    pnl = {}
    for reaction in reactions:
        fair_prices = {k: get_wall_mid(v) for k,v in reaction.input_state.order_depths.items()}
        for reason, trades in reaction.trades.items():
            for trade in trades:
                multiplier = 1 if trade.buyer == "SUBMISSION" else -1
                if reason not in sims:
                    sims[reason] = PnlAccount()
                sims[reason].trade(trade.symbol, trade.price, trade.quantity * multiplier)
        
        pnl = {reason: sim.get_pnl(fair_prices) for reason, sim in sims.items()}
        pnls.append(pnl) # type: ignore
    
    return pnls

def calculate_moving_average(l, window, pad_front=None):
    d = deque()
    if pad_front is not None:
        for _ in range(window):
            d.appendleft(pad_front)
    d_sum = pad_front * window if pad_front else 0
    mas = []
    for li in l:
        d.appendleft(li)
        d_sum += li
        if len(d) > window:
            lj = d.pop()
            d_sum -= lj
        mas.append(d_sum / len(d))
    return mas

def calculate_ema(l, window, multiplier, pad_front=None):
    multiplier_v = np.array([multiplier**k for k in range(window)])

    d = deque()
    if pad_front is not None:
        for _ in range(window):
            d.appendleft(pad_front)
    mas = []
    for li in l:
        d.appendleft(li)
        if len(d) > window:
            d.pop()
        ms,m = 0,0
        for i in range(len(d)):
            ms += d[i] * multiplier_v[i]
            m += multiplier_v[i]
        mas.append(ms / m)
    return mas


def gridsearch_parameters(trader, states: list[TradingState], parameters: dict[str, list[Any]], metric_fn: Callable[[list[Reaction]], Any], use_p3=False) -> list[tuple[Any, dict[str, Any]]]:
    """TODO: fix this"""

    results = []

    combs = [dict(zip(parameters.keys(), comb)) for comb in itertools.product(*parameters.values())]

    for comb in tqdm(combs):
        reactions = local_backtest(trader, states, use_p3, parameters=comb, show_progress=False)
        metric = metric_fn(reactions)
        results.append((metric, comb))

    return sorted(results, key=lambda x: x[0])
def get_pnl_from_trades(trades: list[Trade], mids: list[float]):
    print(f"Getting Pnl from {len(trades)} trades.")
    cash = 0
    position = 0
    pnl = []
    trades_lookup = {}
    for trade in trades:
        if trade.timestamp not in trades_lookup:
            trades_lookup[trade.timestamp] = []
        trades_lookup[trade.timestamp].append(trade)
    for i, price in enumerate(mids):
        timestamp = i * 100
        for trade in trades_lookup.get(timestamp-100, []):
            print("TRADE")
            position += trade.quantity if trade.buyer == "SUBMISSION" else -trade.quantity
            cash -= trade.price * trade.quantity if trade.buyer == "SUBMISSION" else trade.price * -trade.quantity
        pnl.append(cash + position * price)
    return pnl

def fill_forward(l):
    for i in range(1, len(l)):
        if l[i] is None:
            l[i] = l[i-1]
    return l

def fill_backward(l):
    for i in range(len(l)-2,-1,-1):
        if l[i] is None:
            l[i] = l[i+1]
    return l
