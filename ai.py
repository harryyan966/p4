"""Testing Some functions I told Claude to write"""

# TODO: auto-detect mean-reversion and suggest optimal parameters with OU process
# TODO: auto-detect insider trading via bot order quantity & price movement in T timesteps correlation analysis
# TODO: grid-search strategy parameter script


def mean_reversion_analysis(mids: list[float], half_life_window: int = 10) -> dict:
    import numpy as np

    m = np.array(mids, dtype=float)
    if len(m) < 8:
        return {"error": "need at least 8 observations"}

    def _ou_lambda() -> float:
        y, x = np.diff(m), m[:-1] - np.mean(m)
        d = np.dot(x, x)
        return float(np.clip(-np.dot(x, y) / d, 0, 1)) if d > 1e-12 else 0.0

    def _hurst() -> float:
        lags = range(2, max(3, len(m) // 4))
        log_rs, log_lags = [], []
        for lag in lags:
            sub = m[:lag]
            s = np.std(sub, ddof=1)
            if s < 1e-12:
                continue
            devs = np.cumsum(sub - np.mean(sub))
            log_rs.append(np.log(np.ptp(devs) / s))
            log_lags.append(np.log(lag))
        if len(log_rs) < 2:
            return 0.5
        h, _ = np.polyfit(log_lags, log_rs, 1)
        return float(np.clip(h, 0, 1))

    def _adf_tstat() -> float:
        dy, y_lag = np.diff(m), m[:-1] - np.mean(m)
        d = np.dot(y_lag, y_lag)
        if d < 1e-12:
            return 0.0
        beta = np.dot(y_lag, dy) / d
        resid = dy - beta * y_lag
        se = np.sqrt(np.dot(resid, resid) / (len(resid) - 1) / d)
        return float(beta / se) if se > 1e-12 else 0.0

    def _variance_ratio(k: int = 5) -> float:
        if len(m) < k * 2:
            return 1.0
        r1 = np.diff(m)
        rk = m[k:] - m[:-k]
        return float(np.var(rk) / k / (np.var(r1) + 1e-12))

    def _half_life(ou: float) -> float | None:
        return float(-np.log(2) / np.log(1 - ou)) if ou > 1e-4 else None

    def _mid_z() -> float:
        window = m[-half_life_window:]
        return float((m[-1] - np.mean(window)) / (np.std(window) + 1e-12)) if len(window) >= 2 else 0.0

    def _sigmoid(x): return 1 / (1 + np.exp(-x))

    ou  = _ou_lambda()
    h   = _hurst()
    adf = _adf_tstat()   # negative → stationary → reversion
    vr  = _variance_ratio()          # <1 → reversion, >1 → trending
    mz  = _mid_z()

    # normalise each signal to [0,1] where 1 = strong reversion
    ou_sig  = ou                                  # already [0,1]
    h_sig   = 1 - h                               # low H → high signal
    adf_sig = _sigmoid(-adf / 5)                  # more negative t-stat → higher
    vr_sig  = _sigmoid((1 - vr) * 3)              # VR<1 → higher
    mz_sig  = _sigmoid(abs(mz) - 1)              # far from mean → higher

    weights = np.array([0.25, 0.25, 0.25, 0.15, 0.10])
    signals = np.array([ou_sig, h_sig, adf_sig, vr_sig, mz_sig])
    prob    = float(np.dot(weights, signals))

    hl = _half_life(ou)

    if   prob >= 0.70: verdict = "strong mean reversion"
    elif prob >= 0.55: verdict = "moderate mean reversion"
    elif prob >= 0.45: verdict = "neutral / random walk"
    elif prob >= 0.30: verdict = "moderate trending"
    else:              verdict = "strong trending"

    return {
        "snapshots":      len(m),
        "current_mid":    round(float(m[-1]), 4),
        "probability":    round(prob, 4),
        "interpretation": verdict,
        "half_life_ticks": round(hl, 1) if hl else None,
        "components": {
            "ou_lambda":       round(ou, 4),
            "hurst_exponent":  round(h, 4),
            "adf_t_stat":      round(adf, 4),
            "variance_ratio":  round(vr, 4),
            "mid_z_score":     round(mz, 4),
        },
    }

def insider_trading_analysis(states: list["TradingState"], symbol: str, forward_window: int = 10) -> dict:
    import numpy as np
    from collections import defaultdict

    # ── mid price series ──────────────────────────────────────────────────────

    def _mid(od) -> float | None:
        if not od or not od.buy_orders or not od.sell_orders:
            return None
        return (min(od.buy_orders) + max(od.sell_orders)) / 2

    mids = np.array([_mid(s.order_depths.get(symbol)) for s in states], dtype=float)

    # ── collect trades ────────────────────────────────────────────────────────

    # (timestamp_idx, price, qty, side) for own vs market
    own_trades    = []
    market_trades = []

    for i, state in enumerate(states):
        for t in state.own_trades.get(symbol, []):
            side = "buy" if t.quantity > 0 else "sell"
            own_trades.append((i, t.price, abs(t.quantity), side))
        for t in state.market_trades.get(symbol, []):
            side = "buy" if t.quantity > 0 else "sell"
            market_trades.append((i, t.price, abs(t.quantity), side))

    if not own_trades and not market_trades:
        return {"error": f"no trades found for {symbol}"}

    # ── forward return helper ─────────────────────────────────────────────────

    def forward_return(idx: int, side: str) -> float | None:
        fi = min(idx + forward_window, len(mids) - 1)
        m0, m1 = mids[idx], mids[fi]
        if np.isnan(m0) or np.isnan(m1) or m0 < 1e-12:
            return None
        ret = (m1 - m0) / m0
        return ret if side == "buy" else -ret  # positive = trade was correct

    # ── signal 1: adverse selection on own trades ─────────────────────────────
    # if your buys are consistently followed by price drops (and vice versa),
    # someone is trading against you with foreknowledge

    own_returns = [r for t in own_trades if (r := forward_return(t[0], t[3])) is not None]
    own_returns = np.array(own_returns) if own_returns else np.array([])

    own_accuracy      = float(np.mean(own_returns > 0))        if len(own_returns) else 0.5
    own_mean_return   = float(np.mean(own_returns))            if len(own_returns) else 0.0
    adverse_selection = -own_mean_return                        # positive = you're being picked off

    # ── signal 2: market trade anticipation of large moves ────────────────────
    # do market trades cluster just before large price moves?

    valid_mids = mids[~np.isnan(mids)]
    large_move_thresh = np.std(np.diff(valid_mids)) * 2 if len(valid_mids) > 1 else 0.0

    def preceded_large_move(idx: int) -> bool:
        fi = min(idx + forward_window, len(mids) - 1)
        if np.isnan(mids[idx]) or np.isnan(mids[fi]):
            return False
        return abs(mids[fi] - mids[idx]) > large_move_thresh

    market_anticipations = [preceded_large_move(t[0]) for t in market_trades]
    baseline_anticipations = [
        preceded_large_move(i)
        for i in range(len(mids) - forward_window)
        if not np.isnan(mids[i])
    ]

    anticipation_rate    = float(np.mean(market_anticipations))  if market_anticipations    else 0.0
    baseline_rate        = float(np.mean(baseline_anticipations)) if baseline_anticipations else 0.0
    anticipation_edge    = anticipation_rate - baseline_rate

    # ── signal 3: market trade directional accuracy ───────────────────────────

    mkt_returns = [r for t in market_trades if (r := forward_return(t[0], t[3])) is not None]
    mkt_returns = np.array(mkt_returns) if mkt_returns else np.array([])

    mkt_accuracy    = float(np.mean(mkt_returns > 0))  if len(mkt_returns) else 0.5
    mkt_mean_return = float(np.mean(mkt_returns))      if len(mkt_returns) else 0.0

    # ── signal 4: volume spikes before large moves ────────────────────────────

    if market_trades:
        all_qtys          = np.array([t[2] for t in market_trades], dtype=float)
        pre_move_qtys     = [t[2] for t, a in zip(market_trades, market_anticipations) if a]
        non_move_qtys     = [t[2] for t, a in zip(market_trades, market_anticipations) if not a]
        size_before_move  = float(np.mean(pre_move_qtys) / (np.mean(non_move_qtys) + 1e-12)) if pre_move_qtys and non_move_qtys else 1.0
    else:
        size_before_move  = 1.0

    # ── composite suspicion score ─────────────────────────────────────────────

    def sigmoid(x): return 1 / (1 + np.exp(-float(x)))

    adverse_sig     = sigmoid(adverse_selection * 1000)     # being picked off
    anticipation_sig = sigmoid(anticipation_edge * 10)      # front-running moves
    mkt_accuracy_sig = sigmoid((mkt_accuracy - 0.5) * 10)  # market traders winning too often
    size_sig        = sigmoid(size_before_move - 1)         # sizing up before moves

    weights = np.array([0.35, 0.25, 0.25, 0.15])
    signals = np.array([adverse_sig, anticipation_sig, mkt_accuracy_sig, size_sig])
    score   = float(np.dot(weights, signals))

    if   score >= 0.72: verdict = "highly suspicious — likely informed trading"
    elif score >= 0.60: verdict = "moderately suspicious"
    elif score >= 0.50: verdict = "mildly suspicious"
    else:               verdict = "normal"

    return {
        "symbol":           symbol,
        "suspicion_score":  round(score, 4),
        "verdict":          verdict,
        "own_trades":       len(own_trades),
        "market_trades":    len(market_trades),
        "components": {
            "adverse_selection":      round(adverse_selection, 6),   # positive = bad for you
            "own_directional_accuracy": round(own_accuracy, 4),      # your hit rate
            "mkt_directional_accuracy": round(mkt_accuracy, 4),      # market hit rate
            "anticipation_edge":      round(anticipation_edge, 4),   # above baseline
            "size_before_move_ratio": round(size_before_move, 4),    # >1 = suspicious
        },
    }

def turn_anticipation_analysis(states: list["TradingState"], symbol: str, forward_turns: int = 1) -> dict:
    import numpy as np
    from scipy import stats

    # ── mid price per turn ────────────────────────────────────────────────────

    def _mid(od) -> float | None:
        if not od or not od.buy_orders or not od.sell_orders:
            return None
        return (min(od.buy_orders) + max(od.sell_orders)) / 2

    timestamps = [s.timestamp for s in states]
    mids       = np.array([_mid(s.order_depths.get(symbol)) for s in states], dtype=float)
    returns    = np.diff(mids)                          # return[i] = mids[i+1] - mids[i]
    n          = len(states)

    # ── large jump threshold ──────────────────────────────────────────────────

    valid_returns   = returns[~np.isnan(returns)]
    jump_thresh     = np.std(valid_returns) * 1.5       # 1.5σ = "large move"

    # ── per-turn features ─────────────────────────────────────────────────────

    # for each turn i, collect:
    #   - did a market trade occur this turn?
    #   - net signed volume (buys - sells)
    #   - was the next `forward_turns` move a large jump?
    #   - did trade direction agree with the jump direction?

    records = []

    for i in range(n - forward_turns):
        state   = states[i]
        trades  = state.market_trades.get(symbol, [])

        if not trades:
            records.append({
                "timestamp":     timestamps[i],
                "traded":        False,
                "net_volume":    0.0,
                "trade_count":   0,
                "fwd_return":    float(np.nansum(returns[i:i+forward_turns])),
                "is_jump":       False,
                "correct_dir":   None,
            })
            continue

        net_vol    = sum(t.quantity for t in trades)    # positive = net buy
        fwd_return = float(np.nansum(returns[i:i+forward_turns]))
        is_jump    = abs(fwd_return) > jump_thresh
        correct    = (net_vol > 0 and fwd_return > 0) or (net_vol < 0 and fwd_return < 0) if net_vol != 0 else None

        records.append({
            "timestamp":   timestamps[i],
            "traded":      True,
            "net_volume":  float(net_vol),
            "trade_count": len(trades),
            "fwd_return":  fwd_return,
            "is_jump":     is_jump,
            "correct_dir": correct,
        })

    # ── signal 1: do trades preferentially occur before jumps? ───────────────
    # compare P(jump | trade occurred) vs P(jump | no trade)

    traded     = [r for r in records if r["traded"]]
    not_traded = [r for r in records if not r["traded"]]

    p_jump_given_trade    = np.mean([r["is_jump"] for r in traded])     if traded     else 0.0
    p_jump_given_no_trade = np.mean([r["is_jump"] for r in not_traded]) if not_traded else 0.0
    jump_lift             = float(p_jump_given_trade - p_jump_given_no_trade)

    # fisher exact test: is the association statistically significant?
    trade_jump    = sum(1 for r in traded     if     r["is_jump"])
    trade_no_jump = sum(1 for r in traded     if not r["is_jump"])
    no_trade_jump = sum(1 for r in not_traded if     r["is_jump"])
    no_trade_no_jump = sum(1 for r in not_traded if not r["is_jump"])

    # contingency = np.array([[trade_jump, trade_no_jump], [no_trade_jump, no_trade_no_jump]], dtype=float)
    # row_sums    = contingency.sum(axis=1, keepdims=True)
    # col_sums    = contingency.sum(axis=0, keepdims=True)
    # expected    = row_sums * col_sums / contingency.sum()
    # chi2        = float(np.sum((contingency - expected) ** 2 / (expected + 1e-12)))
    # fisher_p    = float(np.exp(-chi2 / 2))          # rough p-value, good enough for flagging'
    a = trade_jump    + 0.5
    b = trade_no_jump + 0.5
    c = no_trade_jump + 0.5
    d = no_trade_no_jump + 0.5
    n = a + b + c + d

    chi2     = n * (a*d - b*c)**2 / ((a+b)*(c+d)*(a+c)*(b+d))
    # chi2 with 1 dof → p-value via log survival
    # log(p) ≈ -chi2/2 for large chi2, avoids underflow
    log_p    = -chi2 / 2
    fisher_p = float(np.exp(log_p)) if log_p > -700 else 0.0  # 0.0 only if truly astronomical


    # ── signal 2: directional accuracy of trades before jumps ────────────────
    # on turns where a trade occurred AND a jump followed, did the net volume
    # point in the right direction?

    jump_turns     = [r for r in traded if r["is_jump"] and r["correct_dir"] is not None]
    dir_accuracy   = float(np.mean([r["correct_dir"] for r in jump_turns])) if jump_turns else 0.5

    # binomial test: is accuracy significantly above 0.5?
    n_correct  = sum(r["correct_dir"] for r in jump_turns)
    binom_z     = (n_correct - len(jump_turns) * 0.5) / (np.sqrt(len(jump_turns) * 0.25) + 1e-12)
    binom_p     = float(1 - (0.5 * (1 + np.sign(binom_z) * (1 - np.exp(-0.7 * binom_z ** 2)))))

    # ── signal 3: volume on pre-jump turns vs normal turns ───────────────────

    pre_jump_vols  = [abs(r["net_volume"]) for r in traded if     r["is_jump"]]
    normal_vols    = [abs(r["net_volume"]) for r in traded if not r["is_jump"]]

    if pre_jump_vols and normal_vols:
        vol_ratio       = float(np.mean(pre_jump_vols) / (np.mean(normal_vols) + 1e-12))
        _, vol_p        = stats.mannwhitneyu(pre_jump_vols, normal_vols, alternative="greater")
    else:
        vol_ratio, vol_p = 1.0, 1.0

    # ── signal 4: are trades suspiciously sparse on non-jump turns? ──────────
    # an informed trader only shows up when they know something is happening

    trade_rate_jump    = p_jump_given_trade
    trade_rate_no_jump = p_jump_given_no_trade
    selectivity        = float(trade_rate_jump - trade_rate_no_jump)   # same as jump_lift, different framing

    # ── composite suspicion score ─────────────────────────────────────────────

    def sigmoid(x): return 1 / (1 + np.exp(-float(x)))

    lift_sig    = sigmoid(jump_lift * 10)
    dir_sig     = sigmoid((dir_accuracy - 0.5) * 10)
    vol_sig     = sigmoid(vol_ratio - 1)
    pval_sig    = 1 - min(fisher_p, 1.0)                               # low p → high signal

    weights = np.array([0.30, 0.30, 0.20, 0.20])
    signals = np.array([lift_sig, dir_sig, vol_sig, pval_sig])
    score   = float(np.dot(weights, signals))

    if   score >= 0.72: verdict = "highly suspicious — trades strongly anticipate jumps"
    elif score >= 0.60: verdict = "moderately suspicious"
    elif score >= 0.50: verdict = "mildly suspicious"
    else:               verdict = "no clear anticipation pattern"

    # ── per-turn breakdown of suspicious turns ────────────────────────────────

    suspicious_turns = [
        {"timestamp": r["timestamp"], "net_volume": r["net_volume"], "fwd_return": round(r["fwd_return"], 4)}
        for r in traded if r["is_jump"] and r["correct_dir"]
    ]

    return {
        "symbol":            symbol,
        "forward_turns":     forward_turns,
        "jump_threshold":    round(float(jump_thresh), 4),
        "total_turns":       len(records),
        "turns_with_trades": len(traded),
        "suspicion_score":   round(score, 4),
        "verdict":           verdict,
        "components": {
            "p_jump_given_trade":    round(float(p_jump_given_trade), 4),
            "p_jump_given_no_trade": round(float(p_jump_given_no_trade), 4),
            "jump_lift":             round(jump_lift, 4),
            "fisher_p_value":        round(float(fisher_p), 4),
            "directional_accuracy":  round(dir_accuracy, 4),
            "binomial_p_value":      round(float(binom_p), 4),
            "volume_ratio":          round(vol_ratio, 4),
            "volume_p_value":        round(float(vol_p), 4),
        },
        # "suspicious_turns":  suspicious_turns,
    }


from utils import *

product = "TOMATOES"
logs = parse_log_strings(get_log_strings("33608"))
states = [get_relevant_state(log.state) for _, log in sorted(logs.items())]
def get_mid(state: TradingState):
    b = min(state.order_depths[product].buy_orders.keys())
    s = max(state.order_depths[product].sell_orders.keys())
    return (b + s) / 2

import matplotlib.pyplot as plt

fig, ax = plt.subplots(2, 1, figsize=(30,10), dpi=300)
ax[0].plot([s.timestamp for s in states], [get_mid(s) for s in states])

def get_trade_size(state: TradingState):
    return sum([t.quantity for t in state.market_trades.get(product, [])])

colors = {0: "red", 1: "orange", 2: "brown", 3: "green", 4: "blue", 5: "indigo", 6: "violet"}

ax[0].scatter(
    [s.timestamp for s in states if s.market_trades.get(product, [])],
    [get_mid(s) for s in states if s.market_trades.get(product, [])],
    s=[get_trade_size(s) * 30 for s in states if s.market_trades.get(product, [])],
    c=[colors[get_trade_size(s) % 7] for s in states if s.market_trades.get(product, [])],
    marker="o"
)

def get_mid_size(state: TradingState):
    b = sorted(state.order_depths[product].buy_orders.items())[2:]
    s = sorted(state.order_depths[product].sell_orders.items())[:-2]
    return sum([q for _, q in b + s])

for t in [s.timestamp for s in states if get_trade_size(s) != 0]:
    ax[0].axvline(t, color="red")

ax[1].plot(
    [s.timestamp for s in states],
    [get_trade_size(s) for s in states]
)

for q in set([get_trade_size(s) for s in states]):
    ax[1].axhline(q, color="red")

# ax[1].scatter(
#     [s.timestamp for s in states if get_mid_size(s) != 0],
#     [get_mid(s) for s in states if get_mid_size(s) != 0],
#     s=[abs(get_mid_size(s)) * 20 for s in states if get_mid_size(s) != 0],
#     c=[colors[abs(get_trade_size(s)) % 7] for s in states if get_mid_size(s) != 0],
#     marker="o"
# )


plt.savefig("image.png")

# print(pretty(mean_reversion_analysis(prices)))
# print(pretty(turn_anticipation_analysis(states, "TOMATOES")))