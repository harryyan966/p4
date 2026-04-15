
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