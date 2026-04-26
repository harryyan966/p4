from lib_data import *
from lib_signal import *
import numpy as np
import matplotlib.pyplot as plt

data = Round3Data(cached=True)
K = 4000

def theo_delta(sigma):
    deltas = delta(data.S(), K, data.TTE(), sigma)
    plt.plot(deltas)
    return np.mean(deltas), np.min(deltas)
def realized_delta(window=10):
    dV = np.array(data.V(K)[window:]) - np.array(data.V(K)[:-window])
    dS = np.array(data.S()[window:]) - np.array(data.S()[:-window])
    d,b = np.polyfit(dS, dV, deg=1)  # dS is x, dV is y
    plt.scatter(dS, dV)
    plt.plot(dS, d*dS + b, color="red")
    return d, b  # d is delta, b is intercept
def realized_sigma(window=1000):
    log_returns = np.diff(np.log(data.S()))
    vols = [
        np.std(log_returns[max(0, i-window):i]) * np.sqrt(10000)
        for i in range(1, len(log_returns)+1)
    ]
    plt.plot(vols[window:])
    return np.mean(vols[window:])

plt.scatter(data.S(), data.S2(), alpha=0.05)

# d, intercept = realized_delta()
# print("Realized Average Delta: ", d)
# d, mind = theo_delta(0.0125)
# print("Theo Delta: ", d)
# sigma = realized_sigma()
# print("Realized Sigma: ", sigma)
plt.show()
