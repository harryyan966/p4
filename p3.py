from p3_utils import *



def trade_rainforest_resin(sims: dict[str, Simulation], data):
    sim = sims["RAINFOREST_RESIN"]
    mid = sim.wall_mid()
    if mid is None:
        return data, {}
    sim.take_all_bids("stable rr price", max_q=sim.ask_quota, min_p=mid+1)
    sim.take_all_asks("stable rr price", max_q=sim.bid_quota, max_p=mid-1)
    target_position = 0
    sim.take_all_bids("flatter rr is better", max_q=sim.position-target_position, min_p=mid)
    sim.take_all_asks("flatter rr is better", max_q=target_position-sim.position, max_p=mid)
    for p,q,r in sim.bids:
        if p + 1 < mid:
            sim.bid(p + 1, sim.bid_quota, "stable rr price")
    for p,q,r in sim.asks:
        if p - 1 > mid:
            sim.ask(p - 1, sim.ask_quota, "stable rr price")
    return sim.orders, data

def trade_kelp(sims: dict[str, Simulation], data):
    sim = sims["KELP"]
    mid = sim.wall_mid()
    if mid is None:
        return data, {}
    sim.take_all_bids("kelp price is stable long term", max_q=sim.ask_quota, min_p=mid+1)
    sim.take_all_asks("kelp price is stable long term", max_q=sim.bid_quota, max_p=mid-1)
    target_position = 0
    sim.take_all_bids("flatter kelp is worth potential lost profit from mid movement", max_q=sim.position-target_position, min_p=mid)
    sim.take_all_asks("flatter kelp is worth potential lost profit from mid movement", max_q=target_position-sim.position, max_p=mid)
    target_position = 0
    for p,q,r in sim.bids:
        if p + 1 < mid:
            sim.bid(p + 1, sim.bid_quota, "kelp price is stable long term and lots of takes exist")
    for p,q,r in sim.asks:
        if p - 1 > mid:
            sim.ask(p - 1, sim.ask_quota, "kelp price is stable long term and lots of takes exit")
    return sim.orders, data

class SquidInkData:
    def __init__(self, data):
        self.prices = data.get("prices", [])
    def to_dict(self):
        return {
            "prices": self.prices
        }

def trade_squid_ink(sims, data_dict):
    sim = sims["SQUID_INK"]
    data = SquidInkData(data_dict)
    return sim.orders, data_dict

BASKET1_PARAMETERS = {
    "hist_mean_premium": 5,
    "n_hist_samples": 60000,
    "spread_threshold": 80,
}
class Basket1Data:
    def __init__(self, data_dict, parameters):
        self.mean_premium = data_dict.get("mean_premium", parameters["hist_mean_premium"])
        self.n = data_dict.get("n", parameters["n_hist_samples"])
        self.pending_orders = data_dict.get("pending_orders", [])
        self.parameters = parameters
        self.spread = None
    def update_basket_spread(self, cp, jp, dp, bp):
        theo = cp * 6 + jp * 3 + dp * 1
        raw_spread = bp - theo
        self.n += 1
        self.mean_premium += (raw_spread - self.mean_premium) / self.n
        self.spread = raw_spread - self.mean_premium
    def update_basket_pending_executions(self, p_thres,q,r):
        self.pending_orders.append((p_thres,q,r))
    def to_dict(self):
        return {
            "mean_premium": self.mean_premium,
            "n": self.n,
            "pending_orders": self.pending_orders,
        }
def trade_basket1(sims: dict[str, Simulation], data_dict, parameters):
    logs = {}
    data = Basket1Data(data_dict, parameters)
    basket = sims["PICNIC_BASKET1"]
    data.update_basket_spread(
        sims["CROISSANTS"].wall_mid(),
        sims["JAMS"].wall_mid(),
        sims["DJEMBES"].wall_mid(),
        basket.wall_mid())
    # TODO expected position
    # TODO hedge?
    # You cannot dismiss an implementation because of its complexity or it "ruins your structure" beacuse your structure is at service to the logic, instead of the other way around.
    # Think take all asks as eat all asks as bidding
    # Think take all bids as eat all bids as asking
    if data.spread is None:
        return basket.orders, data.to_dict(), logs
    baseline = 0
    position_baseline = 0
    spread_threshold = parameters["spread_threshold"]
    if data.spread > baseline + spread_threshold:
        basket.take_all_bids("basket 1 spread mean reverts", max_q=basket.ask_quota)
    if data.spread < baseline and basket.position < position_baseline:
        basket.take_all_asks("basket 1 spread can touch the mid and go back", max_q=position_baseline-basket.position)
    if data.spread < baseline - spread_threshold:
        basket.take_all_asks("basket 1 spread mean reverts", max_q=basket.bid_quota)
    if data.spread > baseline and basket.position > position_baseline:
        basket.take_all_bids("basket 1 spread can touch the mid and go back", max_q=basket.position-position_baseline)
    logs["mean_premium"] = data.mean_premium
    return data.to_dict(), logs





BASKET2_PARAMETERS = {
    "hist_mean_premium": 53,
    "n_hist_samples": 60000,
    "spread_threshold": 50,
}
class Basket2Data:
    def __init__(self, data_dict, parameters):
        self.mean_premium = data_dict.get("mean_premium", parameters["hist_mean_premium"])
        self.n = data_dict.get("n", parameters["n_hist_samples"])
        self.pending_orders = data_dict.get("pending_orders", [])
        self.prev_cp = data_dict.get("prev_cp", None)
        self.prev_jp = data_dict.get("prev_jp", None)
        self.prev_bp = data_dict.get("prev_bp", None)
        self.parameters = parameters
        self.spread = None
    def update_basket_spread(self, cp, jp, bp):
        cp = self.prev_cp if cp is None else cp
        jp = self.prev_jp if jp is None else jp
        bp = self.prev_bp if bp is None else bp
        self.prev_cp = cp
        self.prev_jp = jp
        self.prev_bp = bp
        if cp is None or jp is None or bp is None:
            return
        theo = cp * 4 + jp * 2
        raw_spread = bp - theo
        self.n += 1
        self.mean_premium += (raw_spread - self.mean_premium) / self.n
        self.spread = raw_spread - self.mean_premium
    def update_basket_pending_executions(self, p_thres,q,r):
        self.pending_orders.append((p_thres,q,r))
    def to_dict(self):
        return {
            "mean_premium": self.mean_premium,
            "n": self.n,
            "pending_orders": self.pending_orders,
            "prev_cp": self.prev_cp,
            "prev_jp": self.prev_jp,
            "prev_bp": self.prev_bp,
        }
def trade_basket2(sims: dict[str, Simulation], data_dict, parameters):
    logs = {}
    data = Basket2Data(data_dict, parameters)
    basket = sims["PICNIC_BASKET2"]
    data.update_basket_spread(
        sims["CROISSANTS"].wall_mid(),
        sims["JAMS"].wall_mid(),
        basket.wall_mid())
    if data.spread is None:
        return data.to_dict(), logs
    baseline = 0
    position_baseline = 0
    spread_threshold = parameters["spread_threshold"]
    if data.spread > baseline + spread_threshold:
        basket.take_all_bids("basket 2 spread mean reverts", max_q=basket.ask_quota)
    if data.spread < baseline and basket.position < position_baseline:
        basket.take_all_asks("basket 2 spread can touch the mid and go back", max_q=position_baseline-basket.position)
    if data.spread < baseline - spread_threshold:
        basket.take_all_asks("basket 2 spread mean reverts", max_q=basket.bid_quota)
    if data.spread > baseline and basket.position > position_baseline:
        basket.take_all_bids("basket 2 spread can touch the mid and go back", max_q=basket.position-position_baseline)
    logs["mean_premium"] = data.mean_premium
    return data.to_dict(), logs






PARAMETERS = {
    "trade_basket1": BASKET1_PARAMETERS,
    "trade_basket2": BASKET2_PARAMETERS,
}
class Trader(BaseTrader):
    def get_runners(self):
        return [
            # ("trade_basket1", trade_basket1),
            # ("trade_basket2", trade_basket2),
        ]