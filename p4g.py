import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from utils import *
from p4 import Trader, PARAMETERS


bt_states = get_trading_states_from_data("data_p4/round1", [0, 1, 2], use_p3=False, use_cache=True)
def metric_fn(reactions):
    return sum(get_pnls_from_reactions(reactions)[-1].values())
parameters = {
    "buffer": list(range(20))
}
results = gridsearch_parameters(Trader(), bt_states, use_p3=False, parameters=parameters, metric_fn=metric_fn)
for metric, parameters in results:
    print((metric, parameters))

