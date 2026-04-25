from datamodel import TradingState, Symbol, Order, OrderDepth
import json
from typing import Callable, Any
import numpy as np
import scipy
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



VOL_SCALP_PARAMS = {}
MEAN_REV_PARAMS = {}





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
        return 0.5 * (1.0 + scipy.special.erf(x / np.sqrt(2.0)))
    @staticmethod
    def price(S,K,TTE,sigma,r=0.0):
        sqrt_T = np.sqrt(TTE)
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * TTE) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T
        return S * Math._norm_cdf(d1) - K * np.exp(-r * TTE) * Math._norm_cdf(d2)
    @staticmethod
    def impl_vol(V,S,K,TTE,r=0.0,tol=1e-6):
        return scipy.optimize.brentq(lambda sigma: Math.price(S, K, TTE, sigma, r) - V, 1e-6, 10.0, xtol=tol)



SURFACE_COEFFS = (0.01330605977637028, 0.0038293429398075086, 0.001201017807027063, -8.979584275308355e-05, -0.000470803230326497)

def fitted_vol(m, tte, coeffs):
    a, b, c, d, e = coeffs
    return a + b*m + c*m**2 + d*tte + e*m*tte

def moneyness(S, K, TTE):
    return np.log(S / K) / np.sqrt(TTE)

def iv_surface_mean_reversion(t, sims: dict[str, Simulation], trader_data, parameters):
    S_sim = sims["VELVETFRUIT_EXTRACT"]
    S_mid = S_sim.strict_wall_mid()
    if S_mid is None:
        return {}

    round = 3
    TTE = 8 - round - (t / 1000000)
    if TTE <= 0:
        return {}

    logs = {}
    for K in [5300]:
        if K == 5400 or not 5000<=K<=5500:
            continue
        sim = sims[f"VEV_{K}"]
        V_mid = sim.strict_wall_mid()
        if V_mid is None:
            continue

        # compute implied vol
        try:
            iv = Math.impl_vol(V_mid, S_mid, K, TTE)
        except Exception:
            continue

        # compute surface fair vol and residual
        m = moneyness(S_mid, K, TTE)
        fair_iv = fitted_vol(m, TTE, SURFACE_COEFFS)
        residual = iv - fair_iv

        # track moving average of residual
        resid_data = MovingAverageData(f"resid({K})", trader_data, 500)
        resid_data.update(residual)
        if resid_data.invalid():
            continue

        # fair option price uses surface vol (mean-reverted)
        fair_vol = fair_iv + resid_data.ma  # surface + avg residual
        fair_price = Math.price(S_mid, K, TTE, fair_vol)

        # trade: if current iv is above fair, sell (option is rich); if below, buy
        sim.take_all_asks("iv_surface", max_q=sim.bid_quota, max_p=int(np.floor(fair_price)))
        sim.take_all_bids("iv_surface", max_q=sim.ask_quota, min_p=int(np.ceil(fair_price)))

        logs[K] = {"iv": iv, "fair_iv": fair_iv, "residual": residual, "ma_resid": resid_data.ma, "fair_price": fair_price}

    return logs


def vol_arb_5400(t, sims, trader_data, parameters):
    round = 3
    TTE = 8 - round - (t / 1000000)
    if TTE <= 0:
        return {}

    S_mid = sims["VELVETFRUIT_EXTRACT"].strict_wall_mid()
    if S_mid is None:
        return {}

    # compute vegas to size the hedge
    def vega(S, K, TTE, sigma):
        sqrt_T = np.sqrt(TTE)
        d1 = (np.log(S / K) + 0.5 * sigma**2 * TTE) / (sigma * sqrt_T)
        return S * sqrt_T * np.exp(-0.5 * d1**2) / np.sqrt(2 * np.pi)

    try:
        iv_5400 = Math.impl_vol(sims["VEV_5400"].strict_wall_mid(), S_mid, 5400, TTE)
        iv_5300 = Math.impl_vol(sims["VEV_5300"].strict_wall_mid(), S_mid, 5300, TTE)
        iv_5500 = Math.impl_vol(sims["VEV_5500"].strict_wall_mid(), S_mid, 5500, TTE)
    except Exception:
        return {}

    v_5400 = vega(S_mid, 5400, TTE, iv_5400)
    v_5300 = vega(S_mid, 5300, TTE, iv_5300)
    v_5500 = vega(S_mid, 5500, TTE, iv_5500)

    # buy 5400, sell 5300 and 5500 vega-weighted
    target_5400 = 100
    ratio_5300 = v_5400 / v_5300 * 0.5  # split equally between wings
    ratio_5500 = v_5400 / v_5500 * 0.5
    target_5300 = -int(target_5400 * ratio_5300)
    target_5500 = -int(target_5400 * ratio_5500)

    def trade_to_target(sim, target):
        diff = target - sim.position
        if diff > 0:
            sim.take_all_asks("vol_arb", max_q=diff)
        elif diff < 0:
            sim.take_all_bids("vol_arb", max_q=-diff)

    trade_to_target(sims["VEV_5400"], target_5400)
    trade_to_target(sims["VEV_5300"], target_5300)
    trade_to_target(sims["VEV_5500"], target_5500)

    return {
        "iv_5400": iv_5400, "iv_5300": iv_5300, "iv_5500": iv_5500,
        "target_5300": target_5300, "target_5500": target_5500,
    }

RUNNERS = [
    ("vol_arb_5400", vol_arb_5400),
    # ("iv_surface_mean_reversion", iv_surface_mean_reversion),
]





PARAMETERS = {
    "vol_scalp": VOL_SCALP_PARAMS,
    "mean_rev": MEAN_REV_PARAMS
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
    











# def iv_mean_reversion(t, sims: dict[str, Simulation], trader_data, parameters):
#     V_sims = {K: sims[f"VEV_{K}"] for K in Ks}
#     S_sim = sims["VELVETFRUIT_EXTRACT"]
#     S_data = MovingAverageData("S", trader_data, 1)
#     S_data.update(S_sim.strict_wall_mid())
#     round = 3
#     if S_data.invalid():
#         return ""
#     fairs = {}
#     for K in [5000]:
#         V_data = MovingAverageData(f"V({K})", trader_data, 1)
#         V_data.update(V_sims[K].strict_wall_mid())
#         if V_data.invalid(): continue
#         V,S,TTE = V_data.ff_mid, S_data.ff_mid, (8-round - (t / 10000_00))
#         impl_vol = Math.impl_vol(V,S,K,TTE)
#         sigma_data = MovingAverageData(f"sigma({K})", trader_data, 5000)
#         sigma_data.update(impl_vol)
#         if sigma_data.invalid(): continue
#         ma_fair = Math.price(S,K,TTE,sigma_data.ma) # mayfair!
#         fairs[K] = ma_fair
#         sim = V_sims[K]
#         sim.take_all_asks("impl vol mean reversion", max_q=sim.bid_quota, max_p=np.floor(ma_fair))
#         sim.take_all_bids("impl vol mean reversion", max_q=sim.ask_quota, min_p=np.ceil(ma_fair))
#     return fairs
# RUNNERS = [
#     # ("test", test)
#     ("iv_mean_reversion", iv_mean_reversion)
#     # ("mean_rev", mean_rev),
# ]



















# def trade_pepper_roots(state, data_dict, parameters):
#     sim = Simulation(product="INTARIAN_PEPPER_ROOT", state=state)
#     tol = 1 if state.timestamp < 20_000 else 0
#     while sim.bid_quota > 0 and len(sim.asks) > tol:
#         sim.bid(sim.best_ask(), sim.bid_quota, "buy pepper roots")
#     return sim.orders, data_dict, {}
# OSMIUM_PARAMS = {"ma_window": 20, "spread": 5}
# class OsmiumData:
#     def __init__(self, data_dict, parameters):
#         self.prev_prices = data_dict.get("prev_prices", [])
#         self.informed_direction = data_dict.get("informed_direction", None)
#         self.informed_timestamp = data_dict.get("informed_timestamps", None)
#         self.parameters = parameters
#         self.moving_average = None
#     def update_moving_average(self, mid):
#         if mid is None and len(self.prev_prices) == 0:
#             return
#         elif mid is None:
#             self.prev_prices.append(self.prev_prices[-1])
#         else:
#             self.prev_prices.append(mid)
#         if len(self.prev_prices) > self.parameters["ma_window"]:
#             self.prev_prices.pop(0)
#         self.moving_average = sum(self.prev_prices) / len(self.prev_prices)
#     def to_dict(self):
#         return {
#             "prev_prices": self.prev_prices
#         }
# def trade_osmium(state, data_dict, parameters):
#     sim = Simulation(product="ASH_COATED_OSMIUM", state=state)
#     data = OsmiumData(data_dict, parameters)
#     mid = sim.strict_wall_mid()
#     data.update_moving_average(mid)
#     if data.moving_average is None:
#         return sim.orders, data.to_dict(), {}
#     fair = data.moving_average
#     fair = round(fair)
#     spread = parameters["spread"]

#     sim.take_all_asks("osmium=10000", max_q=sim.bid_quota, max_p=fair-1)
#     sim.take_all_bids("osmium=10000", max_q=sim.ask_quota, min_p=fair+1)
#     # target_position = -30 if fair > 10008 else 30 if fair < 9992 else 0
#     target_position = 0
#     sim.take_all_asks("flatten osmium", max_q=target_position-sim.position, max_p=10000)
#     sim.take_all_bids("flatten osmium", max_q=sim.position-target_position, min_p=10000)

#     for p,q,r in sim.bids:
#         if p + 1 < fair-spread+1:
#             sim.bid(p + 1, sim.bid_quota, "osmium low oscillation around 10000")
#             break
#     for p,q,r in sim.asks:
#         if p - 1 > fair+spread-1:
#             sim.ask(p - 1, sim.ask_quota, "osmium low oscillation around 10000")
#             break
#     return sim.orders, data.to_dict(), {}
