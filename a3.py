from utils import *
from datamodel import *
import matplotlib.pyplot as plt

def visualize_states(states: list[TradingState]):
    products = list(states[0].listings.keys())
    fig,axes = plt.subplots(len(products), 1, figsize=(10, 5 * len(products)))
    if len(products) == 1:
        axes = [axes]
    
    for i in range(len(products)):
        product = products[i]
        ax = axes[i]
        ax.set_title(product)

        bids = [(k,v,s.timestamp) for s in states for k, v in s.order_depths.get(product, OrderDepth()).buy_orders.items()]
        if False: ax.scatter(
            [t for p,q,t in bids],
            [p for p,q,t in bids],
            s = [q for p,q,t in bids],
            color="blue"
        )
        asks = [(k,v,s.timestamp) for s in states for k, v in s.order_depths.get(product, OrderDepth()).sell_orders.items()]
        if False: ax.scatter(
            [t for p,q,t in asks],
            [p for p,q,t in asks],
            s = [abs(q) for p,q,t in asks],
            color="orange"
        )
            
        mids = [(get_wall_mid(s.order_depths.get(product, OrderDepth())), s.timestamp) for s in states]
        ax.plot(
            [t for p,t in mids],
            [p for p,t in mids],
            color="lightblue"
        )
        
        trades = [(t.price,t.quantity,s.timestamp) for s in states for t in s.market_trades.get(product, [])]
        trades = [(p,q,t) for p,q,t in trades if q == 15]
        if True: ax.scatter(
            [t for p,q,t in trades],
            [p for p,q,t in trades],
            s = [q*10 for p,q,t in trades],
            color="red",
            marker="."
        )
        
        


    fig.savefig("image.png")


use_cache = True
# states = get_trading_states_from_data("data_p3/round0", [1], use_p3=True, use_cache=use_cache)
# states1 = get_trading_states_from_data("data_p3/round1", [0,1,2], use_p3=True, use_cache=use_cache)
# states = get_trading_states_from_data("data_p4", [0, 1], use_p3=False, use_cache=use_cache)
states = get_trading_states_from_data("data_p3/round3", [2,3,4], use_p3=True, use_cache=use_cache)

product = "VOLCANIC_ROCK"
trades = [(t.price,t.quantity,s.timestamp) for s in states for t in s.market_trades.get(product, [])]
trade_size = 5
trades = [(p,q,t) for p,q,t in trades if q == trade_size]
mids = {s.timestamp: get_wall_mid(s.order_depths[product]) for s in states}

# sys.exit(f"Number of trades: {len(trades)}")

# future_ranges = list(range(50, 5000, 200))
# future_ranges = [2,4]

# fig, ax = plt.subplots(len(future_ranges), 1, figsize=(8, 4*len(future_ranges)))
# for i in tqdm(range(len(future_ranges))):
#     future_range = future_ranges[i]
#     future_deltas = []
#     previous_deltas = []
#     for p,q,t in trades:
#         future_timestamps = [t + i * 100 for i in range(future_range)]
#         previous_timestamps = [t - (i+1) * 100 for i in range(future_range)]
#         if np.all(np.array(future_timestamps) <= max(mids.keys())) and np.all(np.array(previous_timestamps) >= min(mids.keys())):
#             future_prices = np.array([mids[t] for t in future_timestamps])
#             previous_prices = np.array([mids[t] for t in previous_timestamps])
#             previous_delta = (previous_prices[0]-previous_prices[-1])
#             future_delta = (future_prices[-1]-future_prices[0])
#             previous_deltas.append(previous_delta)
#             # plt.plot(range(future_range), future_prices-future_prices[0])
#     ax[i].set_title(f"With Trade Sizes {trade_size} Future Range: {future_range}")
#     # ax[i].hist(future_deltas,bins=50)
#     ax[i].hist(previous_deltas,bins=50)

# from autils import generate_similar_random_walk
# ts = mids.keys()
# # ps = {t:p for t,p in zip(ts, generate_similar_random_walk(np.array(list(mids.values()))))}
# ps = mids
# fig, ax = plt.subplots(1, 1, figsize=(10, 6))
# future_range = 4000
# paths = []
# # for _,_,t in tqdm(trades):
# for t in tqdm(ts):
#     future_timestamps = [t + (i+1) * 100 for i in range(future_range)]
#     previous_timestamps = [t - (i+1) * 100 for i in range(future_range)]
#     if np.all(np.array(future_timestamps) <= max(ps.keys())) and np.all(np.array(previous_timestamps) >= min(ps.keys())):
#         future_deltas = np.array([ps[ti]-ps[t] for ti in future_timestamps])
#         previous_deltas = np.array([ps[t]-ps[ti] for ti in previous_timestamps])
#         paths.append(future_deltas * previous_deltas)
#         ax.scatter(range(len(future_timestamps)), future_deltas * previous_deltas, alpha=0.01, color="blue")
#     # ax[i].hist(future_deltas,bins=50)``
# ax.plot(np.mean(paths, axis=0), color="red")


from autils import *
ts = list(mids.keys())
# ps = generate_similar_random_walk(np.array(list(mids.values())))
# ps = np.array(generate_random_walk(0, len(ts), 0, 1))
# ps = generate_ou_process(len(ts), theta=0.01)
ps = np.array(list(mids.values()))
fig, ax = plt.subplots(1, 1, figsize=(10, 6))
future_range = 500
paths = []
# for _,_,t in tqdm(trades):
for i in tqdm(range(future_range, len(ts)-future_range)):
    future_deltas = ps[i+1:i+future_range+1] - ps[i]
    previous_deltas = ps[i] - ps[i-future_range:i][::-1]
    paths.append(future_deltas * previous_deltas)
sigma2 = np.var(np.diff(ps))
normalized_paths = np.array(paths) / (np.arange(1, future_range+1) * sigma2)
plt.plot(np.mean(normalized_paths, axis=0))
# ax.scatter(np.tile(range(future_range), len(paths)), np.array(paths).flatten(), alpha=0.01, color="blue", s=1)
# ax.plot(np.mean(paths, axis=0), color="red")
# ax.plot(ps)



# plt.plot(list(mids.values()))
plt.savefig("image.png")