from datamodel import TradingState, Symbol, Order, OrderDepth
import heapq
import json

class MyP4Encoder(json.JSONEncoder):
    def default(self, o):
        d = o.__dict__.copy()
        d["__type__"] = o.__class__.__name__  # embed the type
        return d

class MinHeap:
    def __init__(self, key, size):
        self.key = key
        self.size = size
        self.heap = []
        self.total_size = 0

    def push(self, item):
        heapq.heappush(self.heap, (self.key(item), item))
        self.total_size += self.size(item)

    def top(self):
        return self.heap[0][1]
    
    def pop(self):
        item = heapq.heappop(self.heap)[1]
        self.total_size -= self.size(item)
        return item
    
    def to_list(self):
        items = []
        while self.heap:
            items.append(heapq.heappop(self.heap))
        ret = [item[1] for item in items]
        heapq.heapify(items)
        self.heap = items
        return ret

    def __bool__(self):
        return bool(self.heap)

class Orderer:
    def __init__(self, product, position_limit, position):
        self.product = product
        self.position_limit = position_limit
        self.position = position
        self.buys = MinHeap(key=lambda quote: -quote[0], size=lambda quote: quote[1])
        self.sells = MinHeap(key=lambda quote: quote[0], size=lambda quote: quote[1])

    def sell(self, p, q, t):
        """Pass a positive q"""
        remaining_quota = self.position_limit + self.position - self.sells.total_size
        q = min(q, remaining_quota)
        # if q > remaining_quota:
        #     raise Exception("Too many sell orders. Check your logic.")
        while q:
            if not self.buys:
                self.sells.push((p, q, t)) # add sell order directly and end
                break
            bp, bq, bt = self.buys.top() # best bid
            if bp < p: # best bid lower than our selling price
                self.sells.push((p, q, t)) # add sell order directly and end
                break
            if bq > q: # best bid can absorb our order
                self.buys.pop()
                self.buys.push((bp, bq-q, bt))
                q = 0
            else: # best bid falls
                self.buys.pop()
                q -= bq
    
    def buy(self, p, q, t):
        """Pass a positive q"""
        remaining_quota = self.position_limit - self.position - self.buys.total_size
        q = min(q, remaining_quota)
        # if q > remaining_quota:
        #     raise Exception("Too many buy orders. Check your logic.")
        while q:
            if not self.sells:
                self.buys.push((p, q, t)) # add buy order directly and end
                break
            ap, aq, at = self.sells.top() # best ask
            if ap > p: # best ask higher than our bid
                self.buys.push((p, q, t)) # bid directly
                break
            if aq > q: # best ask can absorb our bid
                self.sells.pop()
                self.sells.push((ap, aq-q, at))
                q = 0
            else: # best ask falls
                self.sells.pop()
                q -= aq

    def sell_rest(self, p, t):
        remaining_quota = self.position_limit + self.position - self.sells.total_size
        if remaining_quota > 0:
            self.sell(p, remaining_quota, t)

    def buy_rest(self, p, t):
        remaining_quota = self.position_limit - self.position - self.buys.total_size
        if remaining_quota > 0:
            self.buy(p, remaining_quota, t)
    
    def get_orders(self) -> list[tuple[Order, str]]:
        buys = [(Order(symbol=self.product, price=p, quantity=q), t) for p, q, t in self.buys.to_list()]
        sells = [(Order(symbol=self.product, price=p, quantity=-q), t) for p, q, t in self.sells.to_list()]
        
        return buys + sells
    

FLAT_MM = "EMERALDS"
MOVING_MM = "TOMATOES"


def trade_flat_mm(state: TradingState, data: dict[str, object]):
    position = state.position.get(FLAT_MM, 0) # TODO: this position is static, if we do something we may doublecount
    market = Orderer(
        product=FLAT_MM,
        position_limit=80,
        position=position
    )
    # Get Bids and Asks (Sorted From Best To Worst)
    order_depths = state.order_depths.get(FLAT_MM, OrderDepth())
    bids = sorted([(p, abs(q)) for p, q in order_depths.buy_orders.items()], reverse=True)
    asks = sorted([(p, abs(q)) for p, q in order_depths.sell_orders.items()])
    mid = (bids[-1][0] + asks[-1][0]) // 2 # Mid = Average(Bid Wall, Ask Wall)

    # Set Initial Market Making Prices To The Wall Prices
    mm_bid = bids[-1][0]
    mm_ask = asks[-1][0]

    # Take Orders And Update Market Making Prices
    # We Don't Market Make Directly Because That Will Consume All Position Allowances
    for bp, bq in bids:
        if bp > mid: # take
            market.sell(bp, bq, "take emeralds")
        elif bp == mid: # take to flat # TODO: make to flat
            market.sell(bp, max(0, min(bq, position)), "flatten emeralds") # max(min_sell, min(max_sell, want_to_sell))
        elif bp+1 < mid: # make
            mm_bid = bp+1
            break
    for ap, aq in asks:
        if ap < mid: # take
            market.buy(ap, aq, "take emeralds")
        elif ap == mid: # take to flat # TODO: make to flat
            market.buy(ap, max(0, min(aq, -position)), "flatten emeralds") # max(min_buy, min(max_buy, want_to_buy))
        elif ap-1 > mid: # make
            mm_ask = ap-1
            break
    # TODO: make to flat
    
    # Create Market Making Orders
    market.buy_rest(mm_bid, "make emeralds")
    market.sell_rest(mm_ask, "make emeralds")

    return market.get_orders(), data

def trade_moving_mm(state: TradingState, data: dict[str, object]):
    position = state.position.get(MOVING_MM, 0)
    market = Orderer(
        product=MOVING_MM,
        position_limit=80,
        position=position
    )
    
    # Get Bids and Asks (Sorted From Best To Worst)
    order_depths = state.order_depths.get(MOVING_MM, OrderDepth())
    bids = sorted([(p, abs(q)) for p, q in order_depths.buy_orders.items()], reverse=True)
    asks = sorted([(p, abs(q)) for p, q in order_depths.sell_orders.items()])
    mid = (bids[-1][0] + asks[-1][0]) // 2 # Mid = Average(Bid Wall, Ask Wall)

    # Set Initial Market Making Prices To The Wall Prices
    mm_bid = bids[-1][0]
    mm_ask = asks[-1][0]

    # Take Orders And Update Market Making Prices
    # We Don't Market Make Directly Because That Will Consume All Position Allowances
    for bp, bq in bids:
        if bp > mid: # take
            market.sell(bp, bq, "take tomatoes")
        elif bp == mid: # take to flat # TODO: make to flat
            market.sell(bp, max(0, min(bq, position)), "flatten tomatoes") # max(min_sell, min(max_sell, want_to_sell))
        elif bp+1 < mid: # make
            mm_bid = bp+1
            break
    for ap, aq in asks:
        if ap < mid: # take
            market.buy(ap, aq, "take tomatoes")
        elif ap == mid: # take to flat # TODO: make to flat
            market.buy(ap, max(0, min(aq, -position)), "flatten tomatoes") # max(min_buy, min(max_buy, want_to_buy))
        elif ap-1 > mid: # make
            mm_ask = ap-1
            break
    
    # Create Market Making Orders
    market.buy_rest(mm_bid, "make tomatoes")
    market.sell_rest(mm_ask, "make tomatoes")

    return market.get_orders(), data

class Trader:
    def local_run(self, state: TradingState, old_trader_data: dict[str, dict[str, object]]) -> tuple[dict[Symbol, list[Order]], int, dict[str, dict[str, object]], dict[str, object]]:
        """
        State in, orders out.
        """

        logged_orders: dict[str, list[tuple[Order, str]]] = {p: [] for p in state.listings.keys()}
        submitted_orders: dict[str, list[Order]] = {p: [] for p in state.listings.keys()}
        new_trader_data: dict[str, dict[str, object]] = {}
        for label, runner in [
            # ("trade_flat_mm", trade_flat_mm),
            ("trade_moving_mm", trade_moving_mm),
        ]:
            trader_data = old_trader_data.get(label, {})
            orders, trader_data = runner(state, trader_data)
            for order, reason in orders:
                logged_orders[order.symbol].append((order, reason))
                submitted_orders[order.symbol].append(order)
            new_trader_data[label] = trader_data
        
        logs = {
            "state": state,
            "orders": logged_orders,
        }

        return submitted_orders, 0, new_trader_data, logs
    
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        """Wrapper of local_run but handles serialization"""

        old_trader_data: dict[str, dict[str, object]] = json.loads(state.traderData) if state.traderData else {} # type: ignore
        submitted_orders, conversion, new_trader_data, logs = self.local_run(state, old_trader_data)
        print(json.dumps(logs, cls=MyP4Encoder))
        return submitted_orders, conversion, json.dumps(new_trader_data, cls=MyP4Encoder)