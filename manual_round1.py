def resolve(bids, asks, my_p, my_q):
    prices = set([p for p,q in bids] + [p for p,q in asks])
    max_volume = 0
    clearing_price = 0
    pnl = 0
    for price in sorted(prices, reverse=True):
        executed_bids = [(p,q) for p,q in bids if p >= price]
        executed_asks = [(p,q) for p,q in asks if p <= price]
        bid_q = sum([q for p,q in executed_bids]) + (my_q if my_p >= price and my_q > 0 else 0)
        ask_q = sum([q for p,q in executed_asks]) + (-my_q if my_p <= price and my_q < 0 else 0)
        volume = min(bid_q, ask_q)
        if volume > max_volume:
            max_volume = volume
            clearing_price = price
            if my_q > 0:
                eaten_q = sum([q for p,q in executed_bids if p >= my_p])
                pnl = min(max(0, volume - eaten_q), my_q) * (30-clearing_price)
            if my_q < 0:
                eaten_q = sum([q for p,q in executed_asks if p <= my_p])
                pnl = min(max(0, volume - eaten_q), -my_q) * (clearing_price-30)
        pass
    return clearing_price,pnl

def resolve2(bids, asks, my_p, my_q):
    prices = set([p for p,q in bids] + [p for p,q in asks])
    max_volume = 0
    clearing_price = 0
    pnl = 0
    for price in sorted(prices, reverse=True):
        executed_bids = [(p,q) for p,q in bids if p >= price]
        executed_asks = [(p,q) for p,q in asks if p <= price]
        bid_q = sum([q for p,q in executed_bids]) + (my_q if my_p >= price and my_q > 0 else 0)
        ask_q = sum([q for p,q in executed_asks]) + (-my_q if my_p <= price and my_q < 0 else 0)
        volume = min(bid_q, ask_q)
        # print(price, volume)
        if volume > max_volume:
            max_volume = volume
            clearing_price = price
            if my_q > 0:
                eaten_q = sum([q for p,q in executed_bids if p >= my_p])
                traded_q = min(max(0, volume - eaten_q), my_q)
                pnl = traded_q * (20-clearing_price) - 0.1 * traded_q
            if my_q < 0:
                eaten_q = sum([q for p,q in executed_asks if p <= my_p])
                traded_q = min(max(0, volume - eaten_q), -my_q)
                pnl = traded_q * (clearing_price-20) - 0.1 * traded_q
        pass
    return clearing_price,pnl

bids = [
    (30, 30),
    (29, 5),
    (28, 12),
    (27, 28),
]
asks = [
    (28, 40),
    (31, 20),
    (32, 20),
    (33, 30),
]

bids2 = [
    (20, 43),
    (19, 17),
    (18, 6),
    (17, 5),
    (16, 10),
    (15, 5),
    (14, 10),
    (13, 7)
]

asks2 = [
    (12, 20),
    (13, 25),
    (14, 35),
    (15, 6),
    (16, 5),
    (18, 10),
    (19, 12),
]

print(resolve2(bids2, asks2, 17, 19.999))

# evals = []
# # import numpy as np
# # for p in set([p for p,q in bids] + [p for p,q in asks]):
# #     for q in range(-200,201):
# #         clearing_price, pnl = resolve(bids, asks, p, q)
# #         evals.append((pnl, p, q, clearing_price))
# # print(sorted(evals, key=lambda x: x[0]))

# for p in set([p for p,q in bids2] + [p for p,q in asks2]):
#     for q in range(-100000, 100001):
#         q = q / 1000
#         clearing_price, pnl = resolve2(bids2, asks2, p, q)
#         evals.append((pnl, p, q, clearing_price))
# print(sorted(evals, key=lambda x: x[0])[-1])


# (p=31, q=9) -> 9 optimal
# (p=20, q=58.699) -> 226.58 optimal