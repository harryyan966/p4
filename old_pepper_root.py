class PepperRootsData:
    def __init__(self, data_dict, parameters):
        self.past_mids = data_dict.get("past_mids", [])
        self.past_mid_bid_dists = data_dict.get("past_mid_bid_dists", [])
        self.past_ask_mid_dists = data_dict.get("past_ask_mid_dists", [])
        self.parameters = parameters
        self.predicted_current_mid = None
        self.average_mid_bid_dist = None
        self.average_ask_mid_dist = None
    def update_predicted_current_mid(self, mid, timestamp):
        self.past_mids.append((timestamp, mid))
        xy = np.array([(t,m) for t,m in self.past_mids if m is not None])
        if len(xy) < self.parameters["min_price_memory"]: return
        if len(xy) > self.parameters["max_price_memory"]:
            self.past_mids.pop(0)
            xy = xy[1:]
        beta, alpha = np.polyfit(xy[:,0],xy[:,1], 1)
        self.predicted_current_mid = beta * timestamp + alpha
    def update_average_mid_bid_dist(self, mid_bid_dist):
        self.past_mid_bid_dists.append(mid_bid_dist)
        if len(self.past_mid_bid_dists) > self.parameters["max_mid_bid_dist_memory"]:
            self.past_mid_bid_dists.pop(0)
        without_none = [m for m in self.past_mid_bid_dists if m is not None]
        self.average_mid_bid_dist = sum(without_none) / len(without_none)
    def update_average_ask_mid_dist(self, ask_mid_dist):
        self.past_ask_mid_dists.append(ask_mid_dist)
        if len(self.past_ask_mid_dists) > self.parameters["max_ask_mid_dist_memory"]:
            self.past_ask_mid_dists.pop(0)
        without_none = [m for m in self.past_ask_mid_dists if m is not None]
        self.average_ask_mid_dist = sum(without_none) / len(without_none)
    def to_dict(self):
        return {
            "past_mids": self.past_mids,
            "past_mid_bid_dists": self.past_mid_bid_dists,
            "past_ask_mid_dists": self.past_ask_mid_dists,
        }

def trade_pepper_roots(state, data_dict, parameters):
    sim = Simulation(product="INTARIAN_PEPPER_ROOT", state=state)
    data = PepperRootsData(data_dict, parameters)
    mid = sim.strict_wall_mid()
    data.update_predicted_current_mid(mid, state.timestamp)   
    fair = data.predicted_current_mid
    if fair is None:
        return sim.orders, data.to_dict(), {}
    while sim.bids and sim.best_bid() > fair and sim.ask_quota > 0:
        sim.take_best_bid("take pepper roots", max_q=sim.ask_quota)
    while sim.asks and sim.best_ask() < fair and sim.bid_quota > 0:
        sim.take_best_ask("take pepper roots", max_q=sim.bid_quota)
    target_position = 40
    while sim.bids and sim.best_bid() >= fair and sim.position > target_position:
        sim.take_best_bid("flatten pepper roots", max_q=sim.position-target_position)
    while sim.asks and sim.best_ask() <= fair and sim.position < target_position:
        sim.take_best_ask("flatten pepper roots", max_q=target_position-sim.position)
    making_bid = None
    for p,q,r in sim.bids:
        if p + 1 < fair:
            making_bid = p + 1
            sim.bid(p + 1, sim.bid_quota, "make pepper roots")
            break
    data.update_average_mid_bid_dist(fair-making_bid if making_bid is not None else None)
    making_ask = None
    for p,q,r in sim.asks:
        if p - 1 > fair:
            making_ask = p - 1
            sim.ask(p - 1, sim.ask_quota, "make pepper roots")
    data.update_average_ask_mid_dist(making_ask-fair if making_ask is not None else None)
    return sim.orders, data.to_dict(), {}
