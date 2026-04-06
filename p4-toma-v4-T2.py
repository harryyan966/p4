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
    POSITION_LIMIT = 80

    position = state.position.get(MOVING_MM, 0)
    market = Orderer(
        product=MOVING_MM,
        position_limit=POSITION_LIMIT,
        position=position
    )

    order_depths = state.order_depths.get(MOVING_MM, OrderDepth())
    bids = sorted([(p, q) for p, q in order_depths.buy_orders.items()], reverse=True)
    asks = sorted([(p, q) for p, q in order_depths.sell_orders.items()])

    if not bids or not asks:
        return []

    best_bid, best_bid_vol = bids[0][0], abs(bids[0][1])
    best_ask, best_ask_vol = asks[0][0], abs(asks[0][1])
    spread = best_ask - best_bid

    # ---------- weighted fair ----------
    total_bid_size = sum(abs(q) for _, q in bids)
    total_ask_size = sum(abs(q) for _, q in asks)

    weighted_bid = sum(p * abs(q) for p, q in bids) / total_bid_size
    weighted_ask = sum(p * abs(q) for p, q in asks) / total_ask_size
    base_fair = (weighted_bid + weighted_ask) / 2

    # ---------- previous weighted mid from traderData ----------
    prev_weighted_mid = None
    if state.traderData:
        try:
            data = jsonpickle.loads(state.traderData)
            prev_weighted_mid = data.get(f"{MOVING_MM}_weighted_mid")
        except Exception:
            prev_weighted_mid = None

    current_price_change = 0.0 if prev_weighted_mid is None else (base_fair - prev_weighted_mid)

    # ---------- inventory term: piecewise, only stronger near the limit ----------
    abs_pos = abs(position)
    if abs_pos <= 30:
        alpha_eff = 0.01
    elif abs_pos <= 60:
        alpha_eff = 0.04
    else:
        alpha_eff = 0.10

    inventory_adjustment = alpha_eff * position

    # ---------- mean-reversion term: only use when move is small/moderate ----------
    beta = 0.10
    if abs(current_price_change) <= 2 and spread <= 3:
        reversion_adjustment = beta * current_price_change
    else:
        reversion_adjustment = 0.0

    # ---------- imbalance term: use normalized imbalance, only if clearly one-sided ----------
    gamma = 0.50
    total_top_vol = best_bid_vol + best_ask_vol
    imbalance = 0.0 if total_top_vol == 0 else (best_bid_vol - best_ask_vol) / total_top_vol

    if abs(imbalance) >= 0.60:
        imbalance_adjustment = gamma * imbalance
    else:
        imbalance_adjustment = 0.0

    fair = (
        base_fair
        - inventory_adjustment
        - reversion_adjustment
        + imbalance_adjustment
    )

    # ---------- detect tiny anomalous inside orders ----------
    next_ask_price = asks[1][0] if len(asks) > 1 else best_ask
    next_bid_price = bids[1][0] if len(bids) > 1 else best_bid
    next_ask_vol = abs(asks[1][1]) if len(asks) > 1 else best_ask_vol
    next_bid_vol = abs(bids[1][1]) if len(bids) > 1 else best_bid_vol

    tiny_inside_ask = (
        spread <= 1
        and len(asks) > 1
        and (next_ask_price - best_ask) >= 2
        and best_ask_vol <= max(3, next_ask_vol // 3)
        and best_ask < fair
    )

    tiny_inside_bid = (
        spread <= 1
        and len(bids) > 1
        and (best_bid - next_bid_price) >= 2
        and best_bid_vol <= max(3, next_bid_vol // 3)
        and best_bid > fair
    )

    ask_start_idx = 0
    bid_start_idx = 0

    # ---------- explicitly grab the tiny anomalous order ----------
    if tiny_inside_ask:
        market.buy(best_ask, best_ask_vol)
        ask_start_idx = 1

    if tiny_inside_bid:
        market.sell(best_bid, best_bid_vol)
        bid_start_idx = 1

    for ap, aq in asks[ask_start_idx:]:
        if ap <= fair - 1:
            market.buy(ap, abs(aq))
        else:
            break

    for bp, bq in bids[bid_start_idx:]:
        if bp >= fair + 1:
            market.sell(bp, abs(bq))
        else:
            break

    # ---------- passive quoting ----------
    # when spread is wide, quote inside the spread
    # but if inventory is already large, bias quoting to inventory-reduction side
    if spread >= 3:
        buy_price = best_bid + 1
        sell_price = best_ask - 1

        if position >= 55:
            # inventory too long: prioritize selling, avoid adding more longs
            if sell_price > fair:
                market.sell_rest(sell_price)

        elif position <= -55:
            # inventory too short: prioritize buying, avoid adding more shorts
            if buy_price < fair:
                market.buy_rest(buy_price)

        else:
            if buy_price < fair:
                market.buy_rest(buy_price)

            if sell_price > fair:
                market.sell_rest(sell_price)

    return market.get_orders()


class Trader:
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        flat_mm_orders = trade_flat_mm(state)
        moving_mm_orders = trade_moving_mm(state)

        od = state.order_depths.get(MOVING_MM, OrderDepth())
        bids = sorted([(p, q) for p, q in od.buy_orders.items()], reverse=True)
        asks = sorted([(p, q) for p, q in od.sell_orders.items()])

        trader_data = {}
        if bids and asks:
            total_bid_size = sum(abs(q) for _, q in bids)
            total_ask_size = sum(abs(q) for _, q in asks)
            weighted_bid = sum(p * abs(q) for p, q in bids) / total_bid_size
            weighted_ask = sum(p * abs(q) for p, q in asks) / total_ask_size
            trader_data[f"{MOVING_MM}_weighted_mid"] = (weighted_bid + weighted_ask) / 2

        all_orders = {FLAT_MM: flat_mm_orders, MOVING_MM: moving_mm_orders}

        print(jsonpickle.dumps({
            "orders": all_orders,
            "state": state,
        }))

        return all_orders, 0, jsonpickle.dumps(trader_data)
