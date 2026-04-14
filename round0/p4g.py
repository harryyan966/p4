import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from utils import *
from p4 import Trader, PARAMETERS

bt_states = get_trading_states_from_log("71415")
# bt_states = get_trading_states_from_data("data_p4", [0, 1], use_p3=False, use_cache=True)
def metric_fn(reactions):
    return sum(get_pnls_from_reactions(reactions)[-1].values())
parameters = {
    "tomato ma window": [20, 30, 40, 50, 60, 70, 80, 90, 100, 140, 180, 200, 220, 250, 300, 400, 500, 600, 700, 800, 1000, 2000]
}
results = gridsearch_parameters(Trader(), bt_states, use_p3=False, parameters=parameters, metric_fn=metric_fn)
for metric, parameters in results:
    print((metric, parameters))

