from datamodel import TradingState, Symbol, Order, OrderDepth
import json
from typing import Callable, Any
import numpy as np
import math
# import scipy
SILENCE_EXCEPTIONS = False
Ks = [4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500]
P4_POSITION_LIMITS = {
    "HYDROGEL_PACK": 200,
    "VELVETFRUIT_EXTRACT": 200,
    **{f"VEV_{K}":300 for K in Ks}
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
    def ask(self, p: int, q, r) -> None:
        """Pass a positive q"""
        q = max(0, q)
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
            if r and br and not SILENCE_EXCEPTIONS:
                raise Exception(f"Your own trades have crossed: {self.orders} {(p,q,r)}.")
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
    def bid(self, p: int, q, r) -> None:
        """Pass a positive q"""
        q = max(0, q)
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
    def take_all_bids(self, reason, max_q, min_p: int|None=None):
        target_ask_quota = max(0, self.ask_quota - max(0,max_q))
        while self.bids and self.ask_quota > target_ask_quota and (min_p is None or self.best_bid() >= min_p):
            self.take_best_bid(reason, self.ask_quota - target_ask_quota)
        return self.ask_quota - target_ask_quota
    def take_all_asks(self, reason, max_q, max_p: int|None=None):
        target_bid_quota = max(0, self.bid_quota - max(0,max_q))
        while self.asks and self.bid_quota > target_bid_quota and (max_p is None or self.best_ask() <= max_p):
            self.take_best_ask(reason, self.bid_quota - target_bid_quota)
        return self.bid_quota - target_bid_quota
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
class MovingAverageData:
    def __init__(self, id, trader_data, window):
        self.key = f"MovingAverageData({id})"
        self.trader_data = trader_data
        self.window = window
        self.data = trader_data.get(self.key, {})
        self.xs = self.data.get("xs", [])
        self.ma = None
        self.ff_mid = None
    def update(self, x):
        if x is None and len(self.xs) == 0:return
        elif x is None:self.xs.append(self.xs[-1])
        else:self.xs.append(x)
        if len(self.xs) > self.window:self.xs.pop(0)
        self.ma = sum(self.xs) / len(self.xs)
        self.ff_mid = self.xs[-1]
        self.settle(self.trader_data)
    def invalid(self):
        return self.ma is None or self.ff_mid is None
    def settle(self, trader_data):
        trader_data[self.key] = {"xs": self.xs}
class Math:
    @staticmethod
    def _norm_cdf(x):
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
    
    @staticmethod
    def price(S, K, TTE, sigma, r=0.0):
        sqrt_T = math.sqrt(TTE)
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * TTE) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T
        return S * Math._norm_cdf(d1) - K * math.exp(-r * TTE) * Math._norm_cdf(d2)
    
    @staticmethod
    def impl_vol(V, S, K, TTE, r=0.0, tol=1e-6):
        lo, hi = 1e-6, 10.0
        for _ in range(100):
            mid = (lo + hi) / 2
            if Math.price(S, K, TTE, mid, r) - V > 0:
                hi = mid
            else:
                lo = mid
            if hi - lo < tol:
                break
        return (lo + hi) / 2
    
    @staticmethod
    def delta(S, K, TTE, sigma, r=0.0):
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * TTE) / (sigma * math.sqrt(TTE))
        return Math._norm_cdf(d1)

LOCAL = True
DAY = 0 if LOCAL else 3


# class Math:
#     @staticmethod
#     def _norm_cdf(x):
#         return 0.5 * (1.0 + scipy.special.erf(x / np.sqrt(2.0)))
#     @staticmethod
#     def price(S,K,TTE,sigma,r=0.0):
#         sqrt_T = np.sqrt(TTE)
#         d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * TTE) / (sigma * sqrt_T)
#         d2 = d1 - sigma * sqrt_T
#         return S * Math._norm_cdf(d1) - K * np.exp(-r * TTE) * Math._norm_cdf(d2)
#     @staticmethod
#     def impl_vol(V,S,K,TTE,r=0.0,tol=1e-6):
#         return scipy.optimize.brentq(lambda sigma: Math.price(S, K, TTE, sigma, r) - V, 1e-6, 10.0, xtol=tol)
#     @staticmethod
#     def delta(S,K,TTE,sigma,r=0.0):
#         d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * TTE) / (sigma * np.sqrt(TTE))
#         return Math._norm_cdf(d1)
class FillForwardData:
    def __init__(self, id, trader_data):
        self.key = f"FillForwardData({id})"
        self.trader_data = trader_data
        self.data = self.trader_data.get(self.key, None)
    def update(self, data):
        if data is not None:
            self.data = data
        self.settle()
        return self.data
    def settle(self):
        self.trader_data[self.key] = self.data


















# def bet_S_with_delta(timestamp, sims: dict[str, Simulation], trader_data, parameters):
#     """Trade S mean reversion with delta of arbitrary K"""
#     start_day = 0
#     S = sims["VELVETFRUIT_EXTRACT"]
#     K = 5300
#     V = sims[f"VEV_{K}"]
#     TTE = (8-start_day) - (timestamp / 10000_00)

#     sigma = 0.0186 # optimize (ma?), currently using fitted implied vol of the strike
#     S_price = FillForwardData("sp", trader_data).update(S.strict_wall_mid())
#     if S_price is None:
#         return "no stock price"
    
#     delta = Math.delta(S_price,K,TTE,sigma)
#     prev_delta = FillForwardData(f"d({K})", trader_data).update(None)
#     if prev_delta is None:
#         prev_delta = FillForwardData(f"d({K})", trader_data).update(delta)
#     if abs(delta-prev_delta) > 3:
#         if S.position > expected_S_position:
#             S.take_all_bids("adjust S", max_q=S.position-expected_S_position)
#         elif S.position < expected_S_position:
#             S.take_all_asks("adjust S", max_q=expected_S_position-S.position)
#     return "success"





# def bet_gamma_hedge_S(timestamp, sims: dict[str, Simulation], trader_data, parameters):
#     """Maintains a constant gamma exposure"""
#     start_day = 0
#     S = sims["VELVETFRUIT_EXTRACT"]
#     TTE = (8-start_day) - (timestamp / 10000_00)

#     S_price = FillForwardData("sp", trader_data).update(S.strict_wall_mid())
#     if S_price is None:
#         return "no stock price"
#     expected_S_position = 120
#     exposed_delta = S.position - 120
#     for K in [5300]:
#         V = sims[f"VEV_{K}"]
#         sigma = 0.0125 # optimize (ma?), currently using fitted implied vol of the strike
#         expected_V_position = V.position_limit
#         # V.take_best_ask("the V exposure", max_q=expected_V_position-V.position)
#         V_position = expected_V_position
    
#         delta = Math.delta(S_price,K,TTE,sigma)
#         exposed_delta += V_position * delta
#         expected_S_position += -V_position * delta
#     if abs(exposed_delta) > 15:
#         if S.position > expected_S_position:
#             S.take_all_bids("adjust S", max_q=S.position-expected_S_position)
#         elif S.position < expected_S_position:
#             S.take_all_asks("adjust S", max_q=expected_S_position-S.position)
#     return "success"






def bet_gamma_hedge_S(timestamp, sims: dict[str, Simulation], trader_data, parameters):
    """sell when up, buy when down"""
    S = sims["VELVETFRUIT_EXTRACT"]
    S_price = FillForwardData("sp", trader_data).update(S.strict_wall_mid())
    if S_price is None:
        return "no stock price"
    S_delta = Math.delta(S_price,5200,8-DAY-(timestamp//10000_00),0.0125)
    last_traded_S_delta = FillForwardData("ltsp", trader_data).data
    if last_traded_S_delta is None:
        last_traded_S_delta = FillForwardData("ltsp", trader_data).update(S_delta)
        FillForwardData("dir", trader_data).update(0)
    direction = FillForwardData("dir", trader_data).data
    if abs(S_delta-last_traded_S_delta) > 0.05:
        FillForwardData("ltsp", trader_data).update(S_delta)
        direction_change = (last_traded_S_delta-S_delta)*1000
        # new_direction = -1 if S_delta > last_traded_S_delta else 1
        direction = FillForwardData("dir", trader_data).update(direction + direction_change)
    expected_S_pos = max(-S.position_limit,min(S.position_limit,int(direction * S.position_limit)))
    if S.position > expected_S_pos:
        S.take_all_bids("take S", max_q=S.position-expected_S_pos)
    elif S.position < expected_S_pos:
        S.take_all_asks("take S", max_q=expected_S_pos-S.position)
    traded_Ks = [5000,5100,5200,5300,5400,5500]
    for K in traded_Ks:
        V = sims[f"VEV_{K}"]
        expected_V_pos = int(direction * V.position_limit)
        if V.position > expected_V_pos:
            V.take_all_bids("take V", max_q=V.position-expected_V_pos)
        elif V.position < expected_V_pos:
            V.take_all_asks("take V", max_q=expected_V_pos-V.position)
    return "success"


def hydrogel(timestamp, sims: dict[str, Simulation], trader_data, parameters):
    """sell when up, buy when down"""
    S = sims["HYDROGEL_PACK"]
    S_price = FillForwardData("sp", trader_data).update(S.strict_wall_mid())
    if S_price is None:
        return "no stock price"
    last_traded_S_price = FillForwardData("ltsp", trader_data).data
    if last_traded_S_price is None:
        last_traded_S_price = FillForwardData("ltsp", trader_data).update(S_price)
        FillForwardData("dir", trader_data).update(0)
    direction = FillForwardData("dir", trader_data).data
    if abs(S_price-last_traded_S_price) > 39:
        FillForwardData("ltsp", trader_data).update(S_price)
        direction_change = (last_traded_S_price-S_price)/40
        # new_direction = -1 if S_delta > last_traded_S_delta else 1
        direction = FillForwardData("dir", trader_data).update(direction + direction_change)
    expected_S_pos = max(-S.position_limit,min(S.position_limit,int(direction * S.position_limit)))
    if S.position > expected_S_pos:
        S.take_all_bids("take S", max_q=S.position-expected_S_pos)
    elif S.position < expected_S_pos:
        S.take_all_asks("take S", max_q=expected_S_pos-S.position)
    return "success"




# def hydrogel_c(timestamp, sims: dict[str, Simulation], trader_data, parameters):
#     """Maintains a constant gamma exposure"""
#     S = sims["HYDROGEL_PACK"]
#     S_price = FillForwardData("sp", trader_data).update(S.strict_wall_mid())
#     prev_prices = FillForwardData("pps", trader_data).data
#     if prev_prices is None:
#         FillForwardData("dir", trader_data).update(0)
#         prev_prices = FillForwardData("pps", trader_data).update([])
#     prev_prices = FillForwardData("pps", trader_data).update([*prev_prices,S_price][-100:])
#     if not prev_prices:
#         return "no stock price"
#     prev_min = prev_prices[0]
#     if S_price-prev_min>30:
#         FillForwardData("dir", trader_data).update(-1)
#     prev_max = prev_prices[0]
#     if prev_max-S_price>30:
#         FillForwardData("dir", trader_data).update(1)
#     direction = FillForwardData("dir", trader_data).data
#     expected_S_pos = direction * S.position_limit
#     if S.position > expected_S_pos:
#         S.take_all_bids("adjust S", max_q=S.position-expected_S_pos)
#     elif S.position < expected_S_pos:
#         S.take_all_asks("adjust S", max_q=expected_S_pos-S.position)
#     return "success"



# def bet_gamma_hedge_V(timestamp, sims: dict[str, Simulation], trader_data, parameters):
#     """Maintains a variable gamma exposure = delta * const"""
#     start_day = 0
#     S = sims["VELVETFRUIT_EXTRACT"]
#     K = 5300
#     V = sims[f"VEV_{K}"]
#     TTE = (8-start_day) - (timestamp / 10000_00)

#     sigma = 0.0125 # optimize (ma?), currently using fitted implied vol of the strike
#     min_allowed_delta = 0.15 # optimize, supporting lower deltas means less position
#     expected_S_position = -V.position_limit * min_allowed_delta
#     S.take_all_bids("the S hedge", max_q=S.position-expected_S_position)

#     S_price = FillForwardData("sp", trader_data).update(S.strict_wall_mid())
#     if S_price is None:
#         return "no stock price"
    
#     S_delta = S.position
#     delta = Math.delta(S_price,K,TTE,sigma)
#     update = (-S_delta) / delta
#     expected_V_position = FillForwardData(f"evp({K})", trader_data).update(update)
#     if expected_V_position is None:
#         return "no expected position"
#     # if timestamp % 100_00 == 0:
    
#     if V.position > expected_V_position:
#         # V.ask(V.best_ask()-1, V.position-expected_V_position, "adjust V")
#         V.take_all_bids("adjust V", max_q=V.position-expected_V_position)
#     elif V.position < expected_V_position:
#         # V.bid(V.best_bid()+1, expected_V_position-V.position, "adjust V")
#         V.take_all_asks("adjust V", max_q=expected_V_position-V.position)
#     return "success"


# Pseudocode
# def bet_gamma(timestamp, sims: dict[str, Simulation], trader_data, parameters):
#     """Maintains a variable gamma exposure = delta * const"""
#     sigma = 0.0125 # optimize (ma?), currently using fitted implied vol of the strike
#     min_allowed_delta = 0.15 # optimize, supporting lower deltas means less available position
#     expected_S_position = -V_position_limit / min_allowed_delta
#     if S_position > expected_S_position:
#         if V_best_bid > threshold:
#             sell_S(expected_V_position-expected_V_position)
#     S_delta = S_position
#     delta = Math.delta(S,K,TTE,sigma)
#     expected_V_position = (-S_delta) / delta
#     if V_position > expected_V_position:
#         if V_best_bid > threshold:
#             sell_V(V_position-expected_V_position)
#     elif V_position < expected_V_position:
#         if V_best_ask < threshold:
#             buy_V(expected_V_position-V_position)
    






















RUNNERS = [
    # ("bet_mean_reversion_S", bet_mean_reversion_S)
    ("bet_gamma_hedge_S", bet_gamma_hedge_S),
    # ("hydrogel", hydrogel)
    # ("mean_reversion_S", mean_reversion_S)
    # ("bet_gamma_hedge_V", bet_gamma_hedge_V)
    # ("hydrogel", hydrogel),
    # ("velvet_fruit", velvet_fruit),
    # ("vol_arb_5400", vol_arb_5400),
    # ("iv_surface_mean_reversion", iv_surface_mean_reversion),
]
PARAMETERS = {
}
class Trader:
    def get_runners(self):
        return RUNNERS
    def local_run(self, state: TradingState, old_trader_data, parameters):
        sims = {product: Simulation(product, state) for product in state.listings.keys()}
        new_trader_data = {}
        orders = {}
        logs = {}
        for label, runner in self.get_runners():
            trader_data = old_trader_data.get(label, {})
            runner_logs = runner(state.timestamp,sims,trader_data,parameters.get(label, {}))
            logs[label] = runner_logs
            new_trader_data[label] = trader_data
        for sim in sims.values():
            for order, reason in sim.orders:
                if reason not in orders:
                    orders[reason] = []
                orders[reason].append(order)
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
