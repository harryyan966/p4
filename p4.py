from datamodel import TradingState, Symbol, Order, OrderDepth
import json
from typing import Callable, Any
import numpy as np

P4_POSITION_LIMITS = {
    "INTARIAN_PEPPER_ROOT": 80,
    "ASH_COATED_OSMIUM": 80,
}

class MyP4Encoder(json.JSONEncoder):
    def default(self, o):
        d = o.__dict__.copy()
        d["__type__"] = o.__class__.__name__  # embed the type
        return d

class SortedList:
    def __init__(self, sorting_key=None) -> None:
        self._data = []
        self._key = sorting_key or (lambda x: x)
    def add(self, item) -> None:
        self._data.append(item)
        self._data.sort(key=self._key)
    def pop(self) -> int:
        return self._data.pop(0)
    def replacetop(self, item) -> int:
        replaced = self._data[0]
        self._data[0] = item
        self._data.sort(key=self._key)
        return replaced
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
    def __init__(self, product, state: TradingState) -> None:
        self.product = product
        self.position_limit = P4_POSITION_LIMITS[product]
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
    def ask(self, p, q, r) -> None:
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
    def bid(self, p, q, r) -> None:
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
    def take_best_bid(self, reason, max_q) -> None:
        p,q,r = self.bids[0]
        self.ask(p, min(q,max_q), reason)
    def take_best_ask(self, reason, max_q) -> None:
        p,q,r = self.asks[0]
        self.bid(p, min(q,max_q), reason)
    def best_bid(self, i=0) -> int:
        p,q,r = self.bids[i]
        return p
    def best_ask(self, i=0) -> int:
        p,q,r = self.asks[i]
        return p
    def ask_wall(self) -> int|None:
        return max([p for p,q,r in self.asks]) if self.asks else None
    def bid_wall(self) -> int|None:
        return min([p for p,q,r in self.bids]) if self.bids else None
    def strict_wall_mid(self) -> float|None:
        if self.ask_wall() is None or self.bid_wall() is None:
            return None
        return (self.ask_wall() + self.bid_wall()) / 2
    def add_order(self, p, q, r) -> None:
        self.orders.append((Order(symbol=self.product, price=p, quantity=q), r))

PEPPER_ROOTS_PARAMS = {
    "buffer": 5,
    "day": 2,
}
def trade_pepper_roots(state, data_dict, parameters):
    sim = Simulation(product="INTARIAN_PEPPER_ROOT", state=state)
    time = state.timestamp//100 + parameters["day"] * 10000
    mid = time * 0.1 + 10000
    # exp_bid = int(mid - 5 - time * (1.5 / (30000-1)))
    exp_ask = int(mid + 6 + time * (1.5 / (30000-1)))
    buffer = 20
    while sim.asks and sim.best_ask() <= exp_ask and sim.bid_quota > buffer:
        sim.take_best_ask("take pepper roots", max_q=sim.bid_quota-buffer)
    while sim.bids and sim.best_bid() > mid and sim.ask_quota > 0:
        sim.take_best_bid("take pepper roots", max_q=sim.ask_quota)
    while sim.asks and sim.best_ask() < mid and sim.bid_quota > 0:
        sim.take_best_ask("take pepper roots", max_q=sim.bid_quota)
    return sim.orders, data_dict, {}

class OsmiumData:
    def __init__(self, data_dict, parameters):
        self.prev_prices = data_dict.get("prev_prices", [])
        self.parameters = parameters
        self.moving_average = None
    def update_moving_average(self, mid):
        self.prev_prices.append(mid)
        if len(self.prev_prices) > self.parameters["ma_window"]:
            self.prev_prices.pop(0)
        without_none = [p for p in self.prev_prices if p is not None]
        if len(without_none) != 0:
            self.moving_average = sum(without_none) / len(without_none)
    def to_dict(self):
        return {
            "prev_prices": self.prev_prices
        }
OSMIUM_PARAMS = {"ma window": 50, "threshold": 3}
def trade_osmium(state, data_dict, parameters):
    sim = Simulation(product="ASH_COATED_OSMIUM", state=state)
    data = OsmiumData(data_dict, parameters)
    mid = sim.strict_wall_mid()
    data.update_moving_average(mid)
    fair = 10000
    threshold = parameters["threshold"]
    buy_threshold = fair - threshold
    sell_threshold = fair + threshold
    if fair is None:
        return sim.orders, data.to_dict(), {}
    while sim.asks and sim.best_ask() < buy_threshold and sim.bid_quota > 0:
        sim.take_best_ask("take osmium", max_q=sim.bid_quota)
    while sim.bids and sim.best_bid() > sell_threshold and sim.ask_quota > 0:
        sim.take_best_bid("take osmium", max_q=sim.ask_quota)
    for p,q,r in sim.bids:
        if p + 1 < fair:
            sim.bid(p + 1, sim.bid_quota, "make pepper roots")
            break
    for p,q,r in sim.asks:
        if p - 1 > fair:
            sim.ask(p - 1, sim.ask_quota, "make pepper roots")
    return sim.orders, data.to_dict(), {}

def trade_osmium_old(state, data_dict, parameters):
    sim = Simulation(product="ASH_COATED_OSMIUM", state=state)
    data = OsmiumData(data_dict, parameters)
    mid = sim.strict_wall_mid()
    data.update_moving_average(mid)
    fair = 10000
    threshold = parameters["threshold"]
    buy_threshold = fair - threshold
    sell_threshold = fair + threshold
    if fair is None:
        return sim.orders, data.to_dict(), {}
    while sim.asks and sim.best_ask() < buy_threshold and sim.bid_quota > 0:
        sim.take_best_ask("take osmium", max_q=sim.bid_quota)
    while sim.bids and sim.best_bid() > sell_threshold and sim.ask_quota > 0:
        sim.take_best_bid("take osmium", max_q=sim.ask_quota)
    for p,q,r in sim.bids:
        if p + 1 < fair:
            sim.bid(p + 1, sim.bid_quota, "make pepper roots")
            break
    for p,q,r in sim.asks:
        if p - 1 > fair:
            sim.ask(p - 1, sim.ask_quota, "make pepper roots")
    return sim.orders, data.to_dict(), {}

def get_relevant_state(state: TradingState):
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
PARAMETERS = {
    "trade_pepper_roots": PEPPER_ROOTS_PARAMS,
    "trade_osmium": OSMIUM_PARAMS,
}
class Trader:
    def get_runners(self):
        return [
            # ("trade_osmium", trade_osmium),
            ("trade_pepper_roots", trade_pepper_roots),
        ]
    def local_run(self, state, old_trader_data, parameters):
        new_trader_data = {}
        orders = {}
        logs = {}
        for label, runner in self.get_runners():
            trader_data = old_trader_data.get(label, {})
            runner_orders, trader_data, runner_logs = runner(get_relevant_state(state), trader_data, parameters.get(label, {}))
            for order, reason in runner_orders:
                if reason not in orders:
                    orders[reason] = []
                orders[reason].append(order)
            new_trader_data[label] = trader_data
            logs[label] = runner_logs
        return orders, 0, new_trader_data, logs
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        """Wrapper of local_run but handles serialization"""
        old_trader_data: dict[str, dict[str, Any]] = json.loads(state.traderData) if state.traderData else {} # type: ignore
        orders, conversion, new_trader_data, logs = self.local_run(state, old_trader_data, PARAMETERS)
        submitted_orders = {}
        for _, reason_orders in orders.items():
            for order in reason_orders:
                if order.symbol not in submitted_orders:
                    submitted_orders[order.symbol] = []
                submitted_orders[order.symbol].append(order)
        print(json.dumps(logs, cls=MyP4Encoder))
        return submitted_orders, conversion, json.dumps(new_trader_data, cls=MyP4Encoder)