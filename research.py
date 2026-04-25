from lib_data import *
from lib_signal import *
import numpy as np
import matplotlib.pyplot as plt

data = Round3Data(cached=True)
deltas = delta(data.S(), 5400, data.TTE(), 0.0186)
plt.plot(deltas)
print(np.max(deltas))
plt.show()

# def realized_vol(prices, ticks_per_day, window=1000):
#     log_returns = np.diff(np.log(prices))
#     vols = [
#         np.std(log_returns[max(0, i-window):i]) * np.sqrt(ticks_per_day)
#         for i in range(1, len(log_returns)+1)
#     ]
#     return vols

# vols = realized_vol(data.S(), ticks_per_day=10000)[1000:]
# plt.plot(vols)
# print(np.mean(vols))
# plt.show()
# # plt.show()