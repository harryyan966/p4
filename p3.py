from p3_utils import *

PARAMETERS = {}

def trade_rainforest_resin(state, data):
    sim = Simulation("RAINFOREST_RESIN", state)
    mid = sim.wall_mid()
    for p,q,r in sim.bids:
        if p > mid:
            sim.take_best_bid("take profitable rainforest resin", max_q=sim.ask_quota)
    for p,q,r in sim.asks:
        if p < mid:
            sim.take_best_ask("take profitable rainforest resin", max_q=sim.bid_quota)
    target_position = 0
    for p,q,r in sim.bids:
        if p == mid and sim.position > target_position:
            sim.take_best_bid("flatten rainforest resin position", max_q=sim.position-target_position)
    for p,q,r in sim.asks:
        if p == mid and sim.position < target_position:
            sim.take_best_ask("flatten rainforest resin position", max_q=target_position-sim.position)
    for p,q,r in sim.bids:
        if p + 1 < mid:
            sim.bid(p + 1, sim.bid_quota, "make rainforest resin")
    for p,q,r in sim.asks:
        if p - 1 > mid:
            sim.ask(p - 1, sim.ask_quota, "make rainforest resin")
    
    return sim.orders, data

def trade_kelp(state, data):
    sim = Simulation("KELP", state)
    mid = sim.wall_mid()
    for p,q,r in sim.bids:
        if p > mid:
            sim.take_best_bid("take profitable kelp", max_q=sim.ask_quota)
    for p,q,r in sim.asks:
        if p < mid:
            sim.take_best_ask("take profitable kelp", max_q=sim.bid_quota)
    target_position = 0
    for p,q,r in sim.bids:
        if p == mid and sim.position > target_position:
            sim.take_best_bid("flatten kelp position", max_q=sim.position-target_position)
    for p,q,r in sim.asks:
        if p == mid and sim.position < target_position:
            sim.take_best_ask("flatten kelp position", max_q=target_position-sim.position)
    for p,q,r in sim.bids:
        if p + 1 < mid:
            sim.bid(p + 1, sim.bid_quota, "make kelp")
    for p,q,r in sim.asks:
        if p - 1 > mid:
            sim.ask(p - 1, sim.ask_quota, "make kelp")
    return sim.orders, data

class SquidInkData:
    def __init__(self, data):
        self.prices = data.get("prices", [])
    def to_dict(self):
        return {
            "prices": self.prices
        }

def trade_squid_ink(state, data_dict):
    sim = Simulation("SQUID_INK", state)
    data = SquidInkData(data_dict)
    return sim.orders, data_dict

# def trade_kelp(state: TradingState, data: dict[str, Any], parameters: dict[str, Any]) -> tuple[list[tuple[Order, str]], dict[str, Any]]:
#     sim = Simulation("SQUID_INK", state)
#     return sim.orders, data

class Trader(BaseTrader):
    def get_runners(self):
        return []