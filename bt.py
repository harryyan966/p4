"""
Backtester.

TODO: support conversions.
"""

from utils import *
import numpy as np
import pandas as pd
from datamodel import Trade, Listing, OrderDepth, TradingState, Observation
from tqdm import tqdm

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

def get_data(max_timestamp = np.inf):
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
    price_df = pd.concat(price_dfs)
    price_df = price_df[price_df["timestamp"] <= max_timestamp]
    trade_df = pd.concat(trade_dfs)
    trade_df = trade_df[trade_df["timestamp"] <= max_timestamp]
    return (price_df, trade_df)

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
    
def generate_trading_states(prices_df: pd.DataFrame, trades_df: pd.DataFrame):
    trading_states: list[TradingState] = []

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
        
    def fill_all(self) -> list[Match]: # this is the pain and the point in implementing time ordering
        all_filled_quotes: list[Match] = []

        quotes = []
        while self.buys:
            quotes.append(self.buys.pop())
        while self.sells:
            quotes.append(self.sells.pop())
        for quote in quotes:
            filled_quotes = self.quote(quote)
            for filled_quote in filled_quotes:
                all_filled_quotes.append(filled_quote)

        return all_filled_quotes

class Simulation:
    def __init__(self, state: TradingState, market_trades: dict[str, list[Trade]] = {}):
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
        for product, trades in market_trades.items():
            book = self.books[product]
            for trade in trades:
                book.quote_without_matching(Quote(trade.buyer, trade.price, trade.quantity))
                book.quote_without_matching(Quote(trade.seller, trade.price, -trade.quantity))
    
    def fill(self, order: Order):
        matches = self.books[order.symbol].quote(Quote("SUBMISSION", order.price, order.quantity))
        return [Trade(
            symbol=order.symbol,
            price=match.buy.price,
            quantity=match.buy.quantity,
            buyer=match.buy.by,
            seller=match.sell.by,
            timestamp=self.state.timestamp
        ) for match in matches]

    def get_market_trades(self):
        """
        Note: this is a destructive function. It destroys the orderbook, preventing it from processing further fills correctly.

        We can make it non-destructive by deepcopying the orderbook, but there is no point doing that given our use case.
        """
        market_trades = {}
        for product, book in self.books.items():
            matches = book.fill_all()
            market_trades[product] = [Trade(
                symbol=product,
                price=match.buy.price,
                quantity=match.buy.quantity,
                buyer=match.buy.by,
                seller=match.sell.by,
                timestamp=self.state.timestamp
            ) for match in matches]
        return market_trades

def backtest(trader, trading_states: list[TradingState]) -> tuple[dict[int, int], dict[int, str]]:
    pnls = {}
    all_logs = {}

    if not trading_states:
        return pnls, all_logs

    cash = 0
    state = trading_states[0]
    for i in tqdm(range(len(trading_states)), desc="Running Backtest"):
        is_last_day = i+1 == len(trading_states)
        next_market_trades = {} if is_last_day else trading_states[i+1].market_trades
        
        product_values = {}
        for product, order_depths in state.order_depths.items():
            product_values[product] = wall_mid_formula(order_depths)

        sim = Simulation(state, market_trades=next_market_trades)
        positions = state.position
        own_trades = {}
        (all_orders, _, traderData), logs = capture_prints(lambda: trader.run(state))
        all_logs[state.timestamp] = logs
        for product, orders in all_orders.items():
            for order in orders:
                trades = sim.fill(order)
                for trade in trades:
                    if product not in own_trades:
                        own_trades[product] = []
                    own_trades[product].append(trade)
                    multiplier = 1 if trade.buyer == "SUBMISSION" else -1
                    if product not in positions:
                        positions[product] = 0
                    positions[product] += trade.quantity * multiplier
                    cash -= trade.price * trade.quantity * multiplier
        position_value = 0
        for product, position in positions.items():
            position_value += product_values[product] * position
        pnls[state.timestamp] = cash + position_value

        if not is_last_day:
            state = TradingState(
                traderData=traderData,
                timestamp=trading_states[i+1].timestamp,
                listings=LISTINGS,
                order_depths=trading_states[i+1].order_depths,
                own_trades=own_trades,
                market_trades=sim.get_market_trades(),
                position=positions,
                observations=Observation(plainValueObservations={}, conversionObservations={})
            )
    
    return pnls, all_logs

try:
    with open("trading_states.cache") as f:
        trading_states: list[TradingState] = [correct_state(s) for s in jsonpickle.loads(f.read())] # type: ignore
except FileNotFoundError:
    prices_df, trades_df = get_data()
    trading_states: list[TradingState] = generate_trading_states(prices_df, trades_df)
    with open("trading_states.cache", "w") as f:
        f.write(jsonpickle.dumps(trading_states)) # type: ignore

from p4 import Trader

# TODO: convert logs to TraderLog and fire analysis like plot2.py
pnls, logs = backtest(Trader(), trading_states)
print([p for t, p in sorted(pnls.items())][-1])
import matplotlib.pyplot as plt

plt.title("Backtest Results")
plt.xlabel("Timestamp")
plt.ylabel("Pnl")
plt.plot([p for t, p in sorted(pnls.items())])
plt.savefig("image.png")