## Useful Tools

### 1. This thing shows your code running time line by line, use it if your code is slow

1. Install the package
```bash
pip install line_profiler
```

2. Decorate the function you want to profile
```python
@profile
def backtest(trader, trading_states, use_logged_orders=True):
    ...
```

3. Run it
```bash
kernprof -l -v your_script.py
```
`-l` enables line-by-line mode, `-v` prints results immediately to stdout. It also saves a your_script.lprof binary file.

4. Reinspect the profiler if you want
```bash
python -m line_profiler your_script.lprof
```







## TODO

### manual trading monte carlo simulation (For Manual Rounds (They are worth A LOT))

**Assigned to Max**

implement the monte carlo simulation thing shown in the frankfurt hedgehogs' github

### black scholes (For Option Round (round3 last year))

**Assigned to Harry (I've done it last year)**

There WILL be an options round, implement curve fitting and options formulas to calculate implied volatility

### mean-reversion detector & parameter finder (For All Instruments with a fair value that we want to exploit)

**Assigned to Harry (I'm interested in this)**

Given a series of prices (perhaps relative to a mean level) and detect whether if exhibits mean-reversion patterns and the threshold & window we should use. 

Also we need to experiment with formulas to calculate the mean (moving average? exponential moving average? special formula?)

One more important insight in mean-reversion exploitation: the mean MUST be hedgeable. For example, you cannot mean revert something to its rolling mean, because you are essentially longing and shorting `price - rolling mean`. If you think price is too high above its rolling mean, you are believing that `price - rolling mean` is too high. In this case, to capitalize this mean reversion, you need to sell `price` AND BUY `rolling mean`. However, you cannot buy `rolling mean`. So however mean-reverting the price is to the rolling mean, you simply cannot exploit it. 

### Understand conversions API and upgrade backtester (For Conversion Rounds)

**Assigned to Harry (I'm familiar with the backtester)**

The conversions round is probably far away but we need to get it because it probably makes a LOT of money. (last year it was the largest earner)

### research on solving position tilt (For Market Making in General)

**Assigned to Max (but don't go too deep as there is probably not THAT much profit in this)**

Position can become extreme and we need to balance it up.
> you are pretty much doing that which is quite important :)

### Find insiders (stretch goal: automatically find insiders by correlating trades) (For rounds 1-4 where no insider information is available, difference between good and excellent.)

**Assigned to Max: correlation analysis**
**Assigned to Harry: implementing changes in trader (I've read frankfurt hedgehog code on this)**

Perhaps correlate trades of different sizes and threshold with price movement within a window, if trades of a certain quantity happens and the prices move a lot then we confident that guy is an insider

Perhaps one step is to label bot trades to different buyers / sellers by quantity? (already semi-supported in the backtester)

### Don't log state in live test, use their provided logs instead.

just speeds the live test up a bit i guess





## Changlogs since apr4 (Thought useful to add so you know what I'm doing)

### distinguish trade reasons in backtester

you can write the reason for each trade in the trader and view trades with different reasons separately once we run the backtest, useful for looking at separate pnls

### support states including `own_trades` in backtester

so we can just pull logs from the website and directly backtest our thing again to show trading reasons. we run everything locally so that we can see the running process and strip useful stuff out of it. 

### Replaced jsonpickle with json

don't use jsonpickle because it will make the backtest extremely slow (this is actually the dominant cost in backtesting). If you want even faster use orjson in the backtester but i didn't mind its fast enough already.

### Separate Backtesting and Pnl Calculation

yeah this is pretty awkward to use but i decided to make the backtester purer so it doesn't do too many things at once. the backtester outputting a list of `Reaction`s is also a pretty clean mental model for me. 

Pnl calculation side can be modified to do more stuff too.

### Implement purely local backtesting

just strips the jsondecode and jsonencode layers and make a new local_run function in the Trader class.

### Add time order to QuoteHeap

ensures orders submitted earlier get filled earlier

### Implement Grid searcher (For All Things Requiring Important Parameters)

Tune trader parameters and see their performance with the local backtester (long running but important to discover parameter dynamics.

Example Usage: 

```python
from utils import * 
from p4 import Trader

states = get_trading_states_from_data()
results = gridsearch_parameters(
    Trader(),
    states,
    parameters={
        "market_making_distance": list(range(1, 3))
        "position_flattening_intensity": list(range(10, 80))
    },
    metric_fn: lambda reactions: sum(get_pnls_from_reactions(reactions)[-1].values()) # final total pnl
)
```