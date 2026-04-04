from statsmodels.tsa.stattools import adfuller
import numpy as np

def hurst_exponent(series: np.ndarray) -> float:
    lags = range(2, min(100, len(series) // 2))
    tau = [np.std(series[lag:] - series[:-lag]) for lag in lags]
    reg = np.polyfit(np.log(lags), np.log(tau), 1)
    return reg[0]

def detect_mean_reversion(values: np.ndarray) -> dict:
    # ADF Test
    adf_result = adfuller(values, autolag="AIC")
    adf_stat, adf_pvalue = adf_result[0], adf_result[1]
    
    # Hurst Exponent
    hurst = hurst_exponent(values)
    
    # Half Life of mean reversion via AR(1) regression
    lagged = values[:-1]
    delta = values[1:] - values[:-1]
    beta = np.polyfit(lagged, delta, 1)[0]
    half_life = -np.log(2) / beta if beta < 0 else np.inf

    # Summary
    is_stationary = adf_pvalue < 0.05
    is_mean_reverting = hurst < 0.5 and is_stationary

    return {
        "is_mean_reverting": is_mean_reverting,
        "adf_statistic": adf_stat,
        "adf_pvalue": adf_pvalue,
        "is_stationary": is_stationary,
        "hurst": hurst,
        "half_life": half_life,  # in number of ticks, how fast it reverts
    }

def generate_similar_random_walk(prices: np.ndarray) -> list[float]:
    diffs = np.diff(prices)
    mu = np.mean(diffs)
    sigma = np.std(diffs)
    
    walk = [prices[0]]
    for _ in range(len(prices) - 1):
        walk.append(walk[-1] + np.random.normal(mu, sigma))
    
    return walk