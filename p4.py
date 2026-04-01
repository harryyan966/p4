from datamodel import TradingState, Symbol, Order, OrderDepth
import jsonpickle
import heapq

FLAT_MM = "EMERALDS"
MOVING_MM = "TOMATOES"

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

    def sell(self, p, q):
        """Pass a positive q"""
        remaining_quota = self.position_limit + self.position - self.sells.total_size
        q = min(q, remaining_quota)
        # if q > remaining_quota:
        #     raise Exception("Too many sell orders. Check your logic.")
        while q:
            if not self.buys:
                self.sells.push((p, q)) # add sell order directly and end
                break
            bp, bq = self.buys.top() # best bid
            if bp < p: # best bid lower than our selling price
                self.sells.push((p, q)) # add sell order directly and end
                break
            if bq > q: # best bid can absorb our order
                self.buys.pop()
                self.buys.push((bp, bq-q))
                q = 0
            else: # best bid falls
                self.buys.pop()
                q -= bq
    
    def buy(self, p, q):
        """Pass a positive q"""
        remaining_quota = self.position_limit - self.position - self.buys.total_size
        q = min(q, remaining_quota)
        # if q > remaining_quota:
        #     raise Exception("Too many buy orders. Check your logic.")
        while q:
            if not self.sells:
                self.buys.push((p, q)) # add buy order directly and end
                break
            ap, aq = self.sells.top() # best ask
            if ap > p: # best ask higher than our bid
                self.buys.push((p, q)) # bid directly
                break
            if aq > q: # best ask can absorb our bid
                self.sells.pop()
                self.sells.push((ap, aq-q))
                q = 0
            else: # best ask falls
                self.sells.pop()
                q -= aq

    def sell_rest(self, p):
        remaining_quota = self.position_limit + self.position - self.sells.total_size
        if remaining_quota > 0:
            self.sell(p, remaining_quota)

    def buy_rest(self, p):
        remaining_quota = self.position_limit - self.position - self.buys.total_size
        if remaining_quota > 0:
            self.buy(p, remaining_quota)
    
    def get_orders(self):
        buys = self.buys.to_list()
        sells = self.sells.to_list()
        bps = []
        bqs = []
        for p, q in buys:
            if not bps or bps[-1] != p:
                bps.append(p)
                bqs.append(q)
            else:
                bqs[-1] += q
        sps = []
        sqs = []
        for p, q in sells:
            if not sps or sps[-1] != p:
                sps.append(p)
                sqs.append(-q)
            else:
                sqs[-1] -= q
                
        return [Order(symbol=self.product, price=p, quantity=q) for p, q in zip(bps + sps, bqs + sqs)]

def trade_flat_mm(state: TradingState):
    position = state.position.get(FLAT_MM, 0) # TODO: this position is static, if we do something we may doublecount
    market = Orderer(
        product=FLAT_MM,
        position_limit=80,
        position=position
    )
    order_depths = state.order_depths.get(FLAT_MM, OrderDepth())
    bids = sorted([(p, q) for p, q in order_depths.buy_orders.items()], reverse=True)
    asks = sorted([(p, q) for p, q in order_depths.sell_orders.items()])
    mid = (bids[-1][0] + asks[-1][0]) // 2 # TODO: verify
    
    # untilt position
    if position > 20:
        market.sell(mid, 10)
    elif position < -20:
        market.buy(mid, 10)
    
    # market take
    for bp, bq in bids: # sell to bids
        if bp > mid:
            market.sell(bp, abs(bq))
    for ap, aq in asks: # buy from asks
        if ap < mid:
            market.buy(ap, abs(aq))
    
    # TODO: position tilt handling

    # undercut by 1 (TODO: try different price levels and check fill activity)
    for bp, bq in bids:
        if bp < mid-1:
            market.buy_rest(bp+1)
            break
    for ap, aq in asks:
        if ap > mid+1:
            market.sell_rest(ap-1)
            break

    return market.get_orders()

def trade_moving_mm(state: TradingState):
    position = state.position.get(MOVING_MM, 0)
    market = Orderer(
        product=MOVING_MM,
        position_limit=80,
        position=position
    )
    order_depths = state.order_depths.get(MOVING_MM, OrderDepth())
    bids = sorted([(p, q) for p, q in order_depths.buy_orders.items()], reverse=True)
    asks = sorted([(p, q) for p, q in order_depths.sell_orders.items()])
    mid = (bids[-1][0] + asks[-1][0]) // 2 # TODO: verify

    # untilt position
    # if position > 20:
    #     market.sell(mid, 10)
    # elif position < -20:
    #     market.buy(mid, 10)

    # market take
    mid -= int(position / 40) # can sell at lower price if position too positive, vice versa
    for bp, bq in bids: # sell to bids
        if bp > mid:
            market.sell(bp, abs(bq))
    for ap, aq in asks: # buy from asks
        if ap < mid:
            market.buy(ap, abs(aq))
    
    # TODO: position tilt handling

    # undercut by k (TODO: try different price levels and check fill activity)
    k = 1
    for bp, bq in bids:
        if bp < mid-1:
            market.buy_rest(bp+k)
            break
    for ap, aq in asks:
        if ap > mid+1:
            market.sell_rest(ap-k)
            break
    
    return market.get_orders()


class Trader:
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        flat_mm_orders = []#trade_flat_mm(state)
        moving_mm_orders = trade_moving_mm(state)

        # maps from product to a list of orders
        all_orders: dict[str, list[Order]] = {FLAT_MM: flat_mm_orders, MOVING_MM: moving_mm_orders}
        print(jsonpickle.dumps({
            "orders": all_orders,
            "state": state
        }))

        return all_orders, 0, ""
