from datamodel import TradingState, Symbol, Order, OrderDepth
import heapq
import json
from typing import Callable, Any
from collections import deque

POSITION_LIMITS = {
    "EMERALDS": 80,
    "TOMATOES": 80,
}

class MyP4Encoder(json.JSONEncoder):
    def default(self, o):
        d = o.__dict__.copy()
        d["__type__"] = o.__class__.__name__  # embed the type
        return d

class SortedList:
    def __init__(self, sorting_key=None):
        self._data = []
        self._key = sorting_key or (lambda x: x)

    def add(self, item):
        self._data.append(item)
        self._data.sort(key=self._key)

    def pop(self):
        return self._data.pop(0)

    def replacetop(self, item):
        self._data[0] = item
        self._data.sort(key=self._key)

    def __getitem__(self, index):
        return self._data[index]

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return f"SortedList({self._data})"

    def __bool__(self):
        return bool(self._data)
    
    def __iter__(self):
        return iter(self._data)

class Simulation:
    def __init__(self, product, state: TradingState):
        self.product = product
        self.position_limit = POSITION_LIMITS[product]
        self.position = state.position.get(product, 0)
        self.bid_quota = self.position_limit - self.position
        self.ask_quota = self.position_limit + self.position
        self.bids = SortedList(sorting_key=lambda quote: -quote[0])
        self.asks = SortedList(sorting_key=lambda quote: quote[0])

        order_depths = state.order_depths.get(self.product, OrderDepth())
        for p,q in order_depths.buy_orders.items():
            self.bid(p,q,"")
        for p,q in order_depths.sell_orders.items():
            self.ask(p,-q,"")
        

    def ask(self, p, q, r):
        """Pass a positive q"""
        if r:
            q = min(q, self.ask_quota)
        while q:
            if not self.bids:
                self.asks.add((p, q, r)) # add sell order directly and end
                if r:
                    self.ask_quota -= q
                break
            bp, bq, br = self.bids[0] # best bid
            if bp < p: # best bid lower than our selling price
                self.asks.add((p, q, r)) # add sell order directly and end
                if r:
                    self.ask_quota -= q
                break
            if r and br:
                raise Exception("Your own trades have crossed.")
            if bq > q: # best bid can absorb our order
                self.bids.replacetop((bp, bq-q, br))
                if r:
                    self.position -= q
                    self.ask_quota -= q
                q = 0
            else: # best bid falls
                self.bids.pop()
                if r:
                    self.position -= bq
                    self.ask_quota -= bq
                q -= bq
    
    def bid(self, p, q, r):
        """Pass a positive q"""
        if r:
            q = min(q, self.bid_quota)
        while q:
            if not self.asks:
                self.bids.add((p, q, r)) # add buy order directly and end
                if r:
                    self.bid_quota -= q
                break
            ap, aq, ar = self.asks[0] # best ask
            if ap > p: # best ask higher than our bid
                self.bids.add((p, q, r)) # bid directly
                if r:
                    self.bid_quota -= q
                break
            if r and ar:
                raise Exception("Your own trades have crossed.")
            if aq > q: # best ask can absorb our bid
                self.asks.replacetop((ap, aq-q, ar))
                if r:
                    self.position += q
                    self.bid_quota -= q
                q = 0
            else: # best ask falls
                self.asks.pop()
                if r:
                    self.position += aq
                    self.bid_quota -= aq
                q -= aq
    
    def take_best_bid(self, reason, max_q=9999):
        p,q,r = self.bids[0]
        self.ask(p, min(q,max_q), reason)
    
    def take_best_ask(self, reason, max_q=9999):
        p,q,r = self.asks[0]
        self.bid(p, min(q,max_q), reason)

    def best_bid(self, i=0):
        p,q,r = self.bids[i]
        return p

    def best_ask(self, i=0):
        p,q,r = self.asks[i]
        return p
    
    def ask_wall(self):
        return max([p for p,q,r in self.asks])
    
    def bid_wall(self):
        return min([p for p,q,r in self.bids])
    
    def wall_mid(self):
        return (self.ask_wall() + self.bid_wall()) / 2

    def orders(self) -> list[tuple[Order, str]]:
        buys = [(Order(symbol=self.product, price=p, quantity=q), r) for p,q,r in self.bids if r]
        sells = [(Order(symbol=self.product, price=p, quantity=-q), r) for p,q,r in self.asks if r]
        
        return buys + sells

def bound(value, mi, mx):
    return max(mi, min(mx, value))

def trade_emeralds(state: TradingState, data: dict[str, Any], parameters: dict[str, Any]):
    sim = Simulation(product="EMERALDS", state=state)

    fair = sim.wall_mid()
    while sim.bids and sim.best_bid() > fair:
        sim.take_best_bid("take emeralds")
    while sim.asks and sim.best_ask() < fair:
        sim.take_best_ask("take emeralds")
    
    while sim.position > 0 and sim.bids and sim.best_bid() == fair:
        sim.take_best_bid("take to flat emeralds", max_q=sim.position)
    while sim.position < 0 and sim.asks and sim.best_ask() == fair:
        sim.take_best_ask("take to flat emeralds", max_q=-sim.position)

    assert sim.bids and sim.asks

    if sim.bids and sim.best_bid() + 1 < fair:
        sim.bid(sim.best_bid() + 1, sim.bid_quota, "make emeralds")
    if sim.asks and sim.best_ask() - 1 > fair:
        sim.ask(sim.best_ask() - 1, sim.ask_quota, "make emeralds")

    return sim.orders(), data

def trade_tomatoes(state: TradingState, data: dict[str, Any], parameters: dict[str, Any]):
    sim = Simulation(product="TOMATOES", state=state)

    mid = sim.wall_mid()
    if "past prices" not in data:
        data["past prices"] = []
    data["past prices"].insert(0, mid)
    if len(data["past prices"]) > parameters["tomato ma window"]:
        data["past prices"].pop()
    moving_average = sum(data["past prices"]) / len(data["past prices"])

    fair = moving_average
    # while sim.bids and sim.best_bid() > fair:
    #     sim.take_best_bid("take tomatoes")
    # while sim.asks and sim.best_ask() < fair:
    #     sim.take_best_ask("take tomatoes")

    if sim.position > 0 and sim.bids and sim.best_bid() == fair:
        sim.take_best_bid("take to flat tomatoes", max_q=sim.position)
    if sim.position < 0 and sim.asks and sim.best_ask() == fair:
        sim.take_best_ask("take to flat tomatoes", max_q=-sim.position)
    
    # if sim.position > 0 and sim.bids and sim.best_bid() < fair:
    #     sim.ask(fair, sim.position, "make to flat tomatoes")
    # if sim.position < 0 and sim.ask and sim.best_ask() > fair:
    #     sim.bid(fair, -sim.position, "make to flat tomatoes")
    
    assert sim.bids and sim.asks

    for p,q,r in sim.bids:
        if p + 1 < fair:
            sim.bid(p + 1, sim.bid_quota, "make tomatoes")
    for p,q,r in sim.asks:
        if p - 1 > fair:
            sim.ask(p - 1, sim.ask_quota, "make tomatoes")

    return sim.orders(), data

class Trader:
    def local_run(self, state: TradingState, old_trader_data: dict[str, dict[str, Any]], parameters: dict[str, Any]) -> tuple[dict[Symbol, list[Order]], int, dict[str, dict[str, Any]], dict[str, Any]]:
        """
        State in, orders out.
        """

        logged_orders: dict[str, list[Order]] = {}
        submitted_orders: dict[str, list[Order]] = {p: [] for p in state.listings.keys()}
        new_trader_data: dict[str, dict[str, Any]] = {}
        runners: list[tuple[str, Callable[[TradingState, dict[str, Any], dict[str, Any]], tuple[list[tuple[Order, str]], dict[str, Any]]]]] = [
            # ("trade_emeralds", trade_emeralds),
            ("trade_tomatoes", trade_tomatoes),
        ]
        for label, runner in runners:
            trader_data = old_trader_data.get(label, {})
            orders, trader_data = runner(state, trader_data, parameters)
            for order, reason in orders:
                if reason not in logged_orders:
                    logged_orders[reason] = []
                logged_orders[reason].append(order)
                submitted_orders[order.symbol].append(order)
            new_trader_data[label] = trader_data
        
        logs = {
            "state": state,
            "orders": logged_orders,
        }

        return submitted_orders, 0, new_trader_data, logs
    
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        """Wrapper of local_run but handles serialization"""

        PARAMETERS = {"tomato ma window": 200}

        old_trader_data: dict[str, dict[str, Any]] = json.loads(state.traderData) if state.traderData else {} # type: ignore
        submitted_orders, conversion, new_trader_data, logs = self.local_run(state, old_trader_data, PARAMETERS)
        print(json.dumps(logs, cls=MyP4Encoder))
        return submitted_orders, conversion, json.dumps(new_trader_data, cls=MyP4Encoder)