import numpy as np
import scipy
from utils import *

def _norm_cdf(x):
    return 0.5 * (1.0 + scipy.special.erf(x / np.sqrt(2.0)))
def call_price(S,K,TTE,r,sigma):
    sqrt_T = np.sqrt(TTE)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * TTE) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return S * _norm_cdf(d1) - K * np.exp(-r * TTE) * _norm_cdf(d2)
@np.vectorize
def impl_vol(V,S,K,TTE,r=0.0,tol=1e-6):
    return scipy.optimize.brentq(lambda sigma: call_price(S, K, TTE, r, sigma) - V, 1e-6, 10.0, xtol=tol)
def ma(l, window, pad_front=None):
    return calculate_moving_average(l,window,pad_front)
def fillup(l):
    return fill_backward(fill_forward(l))
def moneyness(S,K,TTE):
    return np.log(K/S) / TTE*TTE*TTE
def smile_pred_impl_vol(S,K,TTE,a,b,c):
    m = moneyness(S,K,TTE)
    sigma = pred(m,a,b,c)
    return sigma
def smile_pred_price(S,K,TTE,a,b,c):
    return call_price(S,K,TTE,0,smile_pred_impl_vol(S,K,TTE,a,b,c))
def fit(x,y,d):
    return np.polyfit(x,y,d)
def pred(x,a,b,c):
    x = np.array(x)
    return a*x**2+b*x+c
def prem(V,S,K):
    return V-np.maximum(S-K,0)
def delta(S,K,TTE,sigma,r=0.0):
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * TTE) / (sigma * np.sqrt(TTE))
    return _norm_cdf(d1)

# def fit_smile(S,TTE,V):
#     "DEP"
#     Ks = [9500, 9750, 10000, 10250, 10500]
#     m = {}
#     V = {}
#     sigma = {}
#     for K in tqdm(Ks):
#         m[K] = np.log(K/S)/np.sqrt(TTE)
#         sigma[K] = impl_vol(V[K],S,K,TTE)
#     ms = np.array([mi for K in Ks for mi in m[K]])
#     sigmas = np.array([mi for K in Ks for mi in sigma[K]])
#     xy = np.array(sorted([[mi, sigmai] for mi, sigmai in zip(ms, sigmas) if sigmai > 0.005]))
#     a, b, c = np.polyfit(xy[:,0], xy[:,1], 2)

