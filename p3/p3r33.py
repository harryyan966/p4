import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from utils import *
from p3.p3 import Trader, PARAMETERS

# Grab States

use_cache = True
days = [2,3,4]
bt_states = get_trading_states_from_data("data_p3/round3", days, use_p3=True, use_cache=use_cache)
# bt_results = local_backtest(Trader(), bt_states, use_p3=True, parameters=PARAMETERS)
# states = [r.input_state for r in bt_results]
states = bt_states
timestamps = np.array([s.timestamp for s in states])
S = np.array([get_wall_mid(s.order_depths.get("VOLCANIC_ROCK", OrderDepth())) for s in states])
days_left = 7-min(days)
print(timestamps[-5:])
TTE = (days_left - timestamps / 10000_00)
Ks = [9500, 9750, 10000, 10250, 10500]

fig = make_subplots(rows=1+len(Ks), cols=1, shared_xaxes=False, vertical_spacing=0.05)
fig.add_trace(go.Scatter(x=timestamps, y=S, mode="lines", name="S", hovertemplate="time: %{x}<br>price: %{y}"))
fig.update_layout(height=1200, hovermode="x", spikedistance=-1)
fig.update_xaxes(showspikes=True, spikesnap="cursor", spikemode="across", spikedash="solid")
fig.show()
