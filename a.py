from utils import *
from p4_debug import *

states = get_trading_states_from_data(3000, 4000)
for state in states:
    if state.timestamp == 3300:
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
                market.sell(bp, bq)
            elif bp == mid: # take to flat
                market.sell(bp, max(0, min(bq, position))) # max(min_sell, min(max_sell, want_to_sell))
            elif bp+1 < mid: # make
                mm_bid = bp+1
                break
        for ap, aq in asks:
            if ap < mid: # take
                market.buy(ap, aq)
            elif ap == mid: # take to flat
                market.buy(ap, max(0, min(aq, -position))) # max(min_buy, min(max_buy, want_to_buy))
            elif ap-1 > mid: # make
                mm_ask = ap-1
                break
        # TODO: make to flat

        # Create Market Making Orders
        market.buy_rest(mm_bid)
        market.sell_rest(mm_ask)

        print(market.get_orders())