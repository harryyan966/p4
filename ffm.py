"""
My Interpretation of last year's runner-up.

If you can't read this toggle word wrap on in vscode. 

Read their strategy here:
https://github.com/TimoDiehm/imc-prosperity-3

Carries some interesting ideas, but in summary:
1. Follow the insider: Buyer and Seller information become available in the last round. However, in earlier rounds, this team found some anomaly that likely indicated insider trading behavior (certain quantity trades are likely to be profitable etc.). It did some analysis and is tracking insiders with their analysis in earlier rounds. But the code they shared only contains the final submitted code, which simply determines if the book contains an insider with the trader_ids. TODO on our part: look for insiders and follow them. 

2. Mean Reversion: The primary strategy in this IMC competition: the price moves around f(state), calculate f(state) and exploit this behavior. The way these guys exploited this behavior is to define a THRESHOLD. The strategy first calculates f(state) (the mean), then checks whether the price is above or below f(state) by THRESHOLD amount (deviated largely from mean). If so, it bets that the thing will revert to the mean. We need to work on determining those parameters (perhaps fitting it to a so-called OU process (a mean-reverting random walk (stochastic process)) and getting the parameters) or looking for a better exploit of this mean-reversion. One other thing: They also adjusted the mean-reverting thershold based on insider information, so that's also one pain in the ass for implementation. 

3. Market making: use the remaining position for market making if you think the price is stable. If the price is unstable you risk being adverse-selected (people who trade with you know better and you will buy stuff at a shitty price. For example current mid is 10, you buy at 5 and sell at 15, expecting to make 5 per trade, yet somebody knows better and knows the product would skyrocket to 10000, and the guy buys from you at 15. You think you made money but the thing rose to 10000 and uh oh.)

4. Arbitrage: identify easy wins with conversion. For example, you buy a laptop in China, pay a bit to ship it to the US, and sell the laptop in the US. If it is profitable then do it. The crucial thing the team did was identifying taker bots behavior: it implied that the actual price is much more favorable than quoted (a bot constantly scans for stuff in the orderbook and aggressive-takes). TODO on our side: build something to auto-detect this aggressive taking behavior and measure its rate.
"""




from datamodel import *
import numpy as np
import math
from statistics import NormalDist

NORMAL_DISTRIBUTION = NormalDist()

MM = "RAINFOREST_RESIN"
MM_MR = "KELP"
INK = "SQUID_INK"

B1 = "PICNIC_BASKET1"
B2 = "PICNIC_BASKET2"
C1 = "CROISSANTS"
C2 = "JAMS"
C3 = "DJEMBES"

U = "VOLCANIC_ROCK"
O9500 = "VOLCANIC_ROCK_VOUCHER_9500"
O9750 = "VOLCANIC_ROCK_VOUCHER_9750"
O10000 = "VOLCANIC_ROCK_VOUCHER_10000"
O10250 = "VOLCANIC_ROCK_VOUCHER_10250"
O10500 = "VOLCANIC_ROCK_VOUCHER_10500"

F = "MAGNIFICENT_MACARONS"

# POS_LIMITS = {
#     STATIC_SYMBOL: 50, 
#     DYNAMIC_SYMBOL: 50,
#     INK_SYMBOL: 50,
#     ETF_BASKET_SYMBOLS[0]: 60,
#     ETF_BASKET_SYMBOLS[1]: 100,
#     ETF_CONSTITUENT_SYMBOLS[0]: 250,
#     ETF_CONSTITUENT_SYMBOLS[1]: 350,
#     ETF_CONSTITUENT_SYMBOLS[2]: 60,

#     OPTION_UNDERLYING_SYMBOL: 400,
#     **{os: 200 for os in OPTION_SYMBOLS},

#     COMMODITY_SYMBOL: 75,
# }

# CONVERSION_LIMIT = 10

# INSIDER = "Olivia"

# 6, 3, 1; 4, 2, 0
# INITIAL_BASKET_PREMIUM = [5, 53] # TODO(how do you get this?)
# BASKET_THRRESHOLDS = [80, 50]
# n_hist_samples = 60000 TODO(??)
# ETF_THR_INFORMED_ADJS = [90, 90] TODO(??)

# TODO: make a thing that auto-detects informed traders
# TODO: make a orderbook that gets pnl pct for all traders

# THR_OPEN, THR_CLOSE
# LOW_VEGA_THR_ADJ
# THEO_NORM_WINDOW
# iv_scalping_thr # TODO: get thr and window and mean from mean reverting process
# iv_scalping_window
# mean_reversion_thr # how do you get these
# mean_reversion_window
# mean_reversion_thr
# mean_reversion_window



# product_group means "ETF", etc.

# self.total_mkt_buy_volume, .. = get_tota_market_buy_sell_volume() (??)


# Is there a way to better exploit mean reversion other than threshold?
# Can we adjust position or adjust market making (tilt) to do that?

# TODO: incorporate a LIST of informed trades, instead of only the last one.

def trade_mm():
    def profitable(order):
        return order.q < 0 and order.p < mid order.q > 0 and order.p > mid

    for order in orders:
        if profitable(order):
            take(order)
    mm_buy(d=1, include_mid=False)
    mm_sell(d=1, include_mid=False)
    # TODO: overbid the best bid under the mid wall, if best bid is above mid wall, cover the second best. (but i don't think it will contribute THAT much)

def trade_mm_mr():
    
    if informed_long and have_been_long(5): # TODO: how to determine have_been_long parameter
        buy_until_pos_is(40) # TODO: this parameter too
    if wall_pushed_too_in and informed_short:
        bid_at_wall_not_over_it() # TODO but why this
    if informed_short and have_been_short(5):
        sell_until_pos_is(-40)
    if wall_pushed_too_in and informed_long:
        ask_at_wall_not_over_it()
    # TODO: determine how long does the informed trader's thing take effect and how long does it last


def trade_ink():
    if informed_long:
        buy_until_pos_is(POS_POS_LIMIT)
    if informed_short:
        sell_until_pos_is(NEG_POS_LIMIT)
    mm_buy(d=0, include_mid=False)
    mm_sell(d=0, include_mid=False)

def trade_etf():
    delta_from_mean = {}
    for basket in [B1, B2]:
        basket_price = basket.price
        constituents_price_sum = basket.constituents.map(c => c.price).sum()
        if CALCULATE_RUNNING_ETF_PREMIUM: # they set to true, which i think is MAYBE?? correct??
            if basket_premiums_history:
                basket_premium = mean(basket_premiums, max_n=60000) # TODO: where did you get the max_n
                basket_premiums_history.append(basket_premium)
            else:
                basket_premium = basket.initial_premium # TODO: how do you calculate that?
        else:
            basket_premium = basket.initial_premium # constant premium
        delta_from_mean[basket] = basket_price - constituents_price_sum - basket_premium
    
    # buy / sell the basket based on constituent prices instead of the other way around TODO: why?
    for basket in [B1, B2]:
        baseline = informed_long ? 90 : informed_short ? -90 : 0 # TODO: how did you get 90?

        # TODO: find a better way to incorporate informed traders than to adjust the threshold.

        if delta_from_mean[basket] > basket.sell_threshold + baseline:
            sell_all()
        if delta_from_mean[basket] < basket.buy_threshold + baseline:
            buy_all()
        if ETF_CLOSE_AT_ZERO: # they set this to true, which i think is correct.
            if delta_from_mean[basket] > baseline and we_are_buying():
                flat_postiion() # we were buying because price was too low, now price went back. 
            if delta_from_mean[basket] < baseline and we_are_selling():
                flat_postiion() # we were selling because price was too high, now price went back. 
    
    # Trade informed constituent C1
    if informed_long:
        C1.buy_until_pos_is(POS_POS_LIMIT)
    if informed_short:
        C1.sell_until_pos_is(NEG_POS_LIMIT)
    # mm_buy(d=0, include_mid=False)
    # mm_sell(d=0, include_mid=False)

    # Hedge against basket orders (probably not for our case, I believe in the basket mean reversion) also they hedged only with two of the constituents, which i think doesn't make sense at all. If you'd hedge, you'd hedge all of them. Code Omitted. Basically hedge and market make. Market making is stupid too because the thing doesn't even mean-revert.

    # he also says first basket then constituent. Probably artifact in code where get_basket_orders() modify global variable like position or something.


def trade_options():
    def get_theo(underlying, option):
        # TODO: implement correctly
        # TODO: fit volatility smile with moneyness as x axis and implied volatility as y axis and get a bunch of coefficients, which can be used to calculate new implied volatility with moneyness. However, he said this strategy didn't make that much money but the mean-reversion did. What the fuck man LOL
        return theo_price, delta, vega
    
    def calculate_ema(self, current): # TODO: wtf I thought this is exponential moving average no?
        alpha = 2/(window+1) 
        new_mean = alpha * current + (1 - alpha) * old_mean
        return new_mean

    underlying_ema1 = ema(underlying_ema1, underlying.price, window=10) # TODO: why window = 10
    underlying_ema2 = ema(underlying_ema2, underlying.price, window=30) # TODO: why window = 30, why the 10 and the 30
    mean_delta_from_theo = {}
    mean_delta_from_mean_delta_from_theo = {} # TODO which is mean_average_deviation???
    theos = {}
    deltas = {}
    vegas = {}

    if timestamp / 100 < 20:
        do_not_do_anything_with_options()

    for option in options:
        if option.mid is None:
            assume_wall_spread_equals(1)
        # TODO: WHY - 8? WHY DAYS_PER_YEAR
        tte = 1 - (DAYS_PER_YEAR - 8 + DAY + self.state.timestamp // 100 / 10_000) / DAYS_PER_YEAR
        # TODO: why bid_ask_mid? why not wall_mid
        underlying_price = underlying.bid_ask_mid
        theo, delta, vega = get_theo(underlying_price, option.strike, tte)
        theos[option] = theo
        deltas[option] = delta
        vegas[option] = vega
        mean_delta_from_theo[option] = ema(mean_delta_from_theo[option], option.mid - theo, window=20) # TODO: what is THEO_NORM_WINDOW=20??
        mean_delta_from_mean_delta_from_theo[option] = ema(mean_delta_from_mean_delta_from_theo[option], abs((option.mid - theo) - mean_delta_from_theo[option]), window=100) # TODO: what is IV_SCALPING_WINDOW=100?? TODO what is this thing, a second order deviation moving average? why would anyone need that?

    # TODO: think of a better way than to just buy all sell all... Its pretty shitty in my opinion
    
    # TODO: we need analysis on whether the calls are worth scalping (1-lag negative autocorrelation in returns)
    for option in [O9750, O10000, O10250, O10500]:
        if self.mean_delta_from_mean_delta_from_theo >= IV_SCALPING_THR: # TODO: why IV_SCALPING_THR = 0.7, TODO why the name new_switch_mean? TODO why use this indicator?
            theo = theos[option]
            price_minus_theo_mean = mean_delta_from_theo[option]

            low_vega_adj = 0.5 if vegas[option] <= 1 else 0 # TODO: what is low vega threshold adj? if you have this low vega adj your thresholds for open are higher.

            if option.best_bid - theo - price_minus_theo_mean >= (THRES_OPEN + low_vega_adj): # THRES_OPEN = 0.5 means you open order when you cross 0.5
                sell_all()
            
            if option.best_bid - theo - price_minus_theo_mean >= THRES_CLOSE and we_bought(): # THRES_CLOSE = 0, if we bought because its too low and we now wanna close then we close
                flat_position()

            if option.best_ask - theo - price_minus_theo_mean <= -(THRES_OPEN + low_vega_adj): 
                buy_all()
            
            if option.best_ask - theo - price_minus_theo_mean <= -THRES_CLOSE and we_sold(): # TODO: why negative thres close
                flat_position()
        else:

            # TODO: why the fuck 
            if is_long_option():
                sell(best_bid)
            elif short_option():
                buy(best_ask)
    
    # TODO: do gamma scalping right.

    # Mean Reversion
    for option in [O9500]: # TODO MOST IN THE MONEY OPTION, but why?
        current_deviation = underlying.mid - underlying_ema2
        iv_deviation = option.mid - theos[option] - mean_delta_from_theo[option]
        current_deviation += iv_deviation # TODO: why??

        if current_deviation > OPTIONS_MEAN_REVERSION_THRESHOLD and option.can_sell(): # TODO: why OP_MEAN_REVERSION_THRES = 0.5? 
            sell_all()
        
        elif current_deviation < -OPTIONS_MEAN_REVERSION_THRESHOLD and option.can_buy():
            buy_all()
        
        # TODO: why not stop in the middle?

    if timestamp / 100 < UNDERLYING_MEAN_REVERSION_WINDOW: # TODO why underlying mean reversion window = 10?? 
        do_nothing_with_underlying()

    current_deviation = underlying.mid - underlying_ema2 # TODO: what is with this EMA2? I increasingly don't get it.

    if current_deviation > UNDERLYING_MEAN_REVERSION_THR and can_sell(): # TODO: why underlying mean reversion thr = 15
        sell_all()
    if current_deviation < UNDERLYING_MEAN_REVERSION_THR and can_buy():
        buy_all()
    
    # TODO: why not flat out at zero?
    # TODO: should we implement some convenience funciton for this mean reversion thing?
    
    

def trade_loc_arb():
    """
    "a taker bot existed that aggressively filled orders offered at attractive prices relative to a hidden "fair value."
    
    TODO: WE ABSOLUTELY MUST CAPTURE SUCH OPPORTUNITIES

    "In hindsight, quoting larger sizes (e.g., 20–30 units) would have allowed us to profitably convert surplus inventory even on non-fills, squeezing out closer to full optimal performance."

    TODO: WE ABSOLUTELY MUST IMPLEMENT THAT THIS YEAR

    "This taker bot executed approximately 60% of eligible trades"

    TODO: figure out why this relates to the 0.42 in the code
    """

    bid, ask = get_external_bid_and_ask()

    # TODO: how did you get these? What do they mean?
    local_sell_price: int = si_she_wu_ru(bid) # math.floor(bid + 0.5)
    local_buy_price: int = si_she_wu_ru(ask - 0.5) # math.ceil(ask - 0.5)

    external_buy_price = ask + import_tarrif + transport_fees
    external_sell_price = bid + export_tarrif + transport_fees

    local_sell_profit = local_sell_price - external_buy_price
    local_buy_profit = external_sell_price - local_buy_price - 0.1 # storage cost TODO what if you store for more than one day

    # TODO: this year maybe nonzero time for delivery or scale transport cost with delivery time...

    mean_local_sell_profit = mean(local_sell_profits_10_days)
    mean_local_buy_profit = mean(local_buy_profits_10_days)

    # TODO: why do only one kind??
    if local_sell_profit > local_buy_profit:
        # TODO: why need mean local sell profit?
        if local_sell_profit >= 0 and mean_local_sell_profit > 0:
            for bid in bids:
                if (0.42 * local_sell_profit) - (local_sell_price - bid.price) > 0: # if a fraction of the local sell profit - market taking cost is positive then sell TODO: why 0.42 what the fuck is that??
                    sell_and_update_conversion_limit(bid.price)
            # TODO if you sell the remaining and the external price changed what would you do?
            sell_remaining_at(local_sell_price)
    else:
        if local_buy_profit >= 0 and mean_local_buy_profit > 0:
            for ask in asks:
                if (0.42 * local_buy_profit - (ask.price - local_buy_price)) > 0:
                    buy_and_update_conversion_limit(ask.price)
            buy_remaining_at(local_buy_price)
    
    conversion = conversions_required_to_flat_out()
    







# TODO: error handling
# TODO: dict.update
# TODO: they also have a bunch of validity checks in the options section, why?
# TODO: some sell-alls are directed towards bid_wall + 1 instead of just the bid_wall. be careful. and also why?
# TODO: "Autocorrelation analysis of Volcanic Rock returns, compared against randomized normal samples, confirmed significant short-term negative autocorrelation at various horizons,"
# TODO: consider scaling by volatility in all mean-reversion models.