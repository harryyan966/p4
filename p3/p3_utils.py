import json
from utils import P3_POSITION_LIMITS, get_relevant_state
from datamodel import TradingState, Symbol, Order, OrderDepth
import heapq
import json
from typing import Callable, Any
from collections import deque

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
        return iter(list(self._data))

class Simulation:
    def __init__(self, product, state: TradingState):
        self.timestamp = state.timestamp
        self.product = product
        self.position_limit = P3_POSITION_LIMITS[product]
        self.position = state.position.get(product, 0)
        self.bid_quota = self.position_limit - self.position
        self.ask_quota = self.position_limit + self.position
        self.bids = SortedList(sorting_key=lambda quote: -quote[0])
        self.asks = SortedList(sorting_key=lambda quote: quote[0])
        self.orders = []

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
                    self.add_order(p, -q, r)
                break
            bp, bq, br = self.bids[0] # best bid
            if bp < p: # best bid lower than our selling price
                self.asks.add((p, q, r)) # add sell order directly and end
                if r:
                    self.ask_quota -= q
                    self.add_order(p, -q, r)
                break
            if r and br:
                raise Exception("Your own trades have crossed.")
            if bq > q: # best bid can absorb our order
                self.bids.replacetop((bp, bq-q, br))
                if r:
                    self.position -= q
                    self.ask_quota -= q
                    self.add_order(bp, -q, r)
                q = 0
            else: # best bid falls
                self.bids.pop()
                if r:
                    self.position -= bq
                    self.ask_quota -= bq
                    self.add_order(bp, -bq, r)
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
                    self.add_order(p, q, r)
                break
            ap, aq, ar = self.asks[0] # best ask
            if ap > p: # best ask higher than our bid
                self.bids.add((p, q, r)) # bid directly
                if r:
                    self.bid_quota -= q
                    self.add_order(p, q, r)
                break
            if r and ar:
                raise Exception("Your own trades have crossed.")
            if aq > q: # best ask can absorb our bid
                self.asks.replacetop((ap, aq-q, ar))
                if r:
                    self.position += q
                    self.bid_quota -= q
                    self.add_order(ap, q, r)
                q = 0
            else: # best ask falls
                self.asks.pop()
                if r:
                    self.position += aq
                    self.bid_quota -= aq
                    self.add_order(ap, aq, r)
                q -= aq
    
    def take_best_bid(self, reason, max_q):
        p,q,r = self.bids[0]
        self.ask(p, min(q,max_q), reason)
    
    def take_best_ask(self, reason, max_q):
        p,q,r = self.asks[0]
        self.bid(p, min(q,max_q), reason)

    def best_bid(self, i=0):
        p,q,r = self.bids[i]
        return p

    def best_ask(self, i=0):
        p,q,r = self.asks[i]
        return p
    
    def take_all_bids(self, reason, max_q, min_p=None):
        target_ask_quota = max(0, self.ask_quota - max_q)
        while self.bids and self.ask_quota > target_ask_quota and (min_p is None or self.best_bid() >= min_p):
            self.take_best_bid(reason, self.ask_quota - target_ask_quota)
        return self.ask_quota - target_ask_quota
    
    def take_all_asks(self, reason, max_q, max_p=None):
        target_bid_quota = max(0, self.bid_quota - max_q)
        while self.asks and self.bid_quota > target_bid_quota and (max_p is None or self.best_ask() <= max_p):
            self.take_best_ask(reason, self.bid_quota - target_bid_quota)
        return self.bid_quota - target_bid_quota
    
    def execute(self, p_thres, q, r):
        if q < 0:
            return self.take_all_bids(r, max_q=-q, min_p=p_thres)
        if q > 0:
            return self.take_all_asks(r, max_q=-q, max_p=p_thres)
    
    def ask_wall(self) -> int|None:
        return max([p for p,q,r in self.asks]) if self.asks else None
    def bid_wall(self) -> int|None:
        return min([p for p,q,r in self.bids]) if self.bids else None
    def wall_mid(self) -> float|None:
        if self.ask_wall() is None or self.bid_wall() is None:
            return None
        return (self.ask_wall() + self.bid_wall()) / 2

    def add_order(self, p, q, r):
        self.orders.append((Order(symbol=self.product, price=p, quantity=q), r))

class BaseTrader:
    def get_runners(self):
        return []

    def local_run(self, state: TradingState, old_trader_data, parameters):
        sims = {product: Simulation(product, state) for product in state.listings.keys()}
        new_trader_data = {}
        orders = {}
        logs = {}
        for label, runner in self.get_runners():
            trader_data = old_trader_data.get(label, {})
            trader_data, runner_logs = runner(sims, trader_data, parameters.get(label, {}))
            logs[label] = runner_logs
            new_trader_data[label] = trader_data
        for sim in sims.values():
            for order, reason in sim.orders:
                if reason not in orders:
                    orders[reason] = []
                orders[reason].append(order)
        return orders, 0, new_trader_data, logs
    