import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from lib_data import Round3Data
from utils import *

plotly_colors = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52"]

class Picture:
    def __init__(self, x, baseline):
        self.traces: list[go.Scatter] = []
        self.secondary_traces: list[go.Scatter] = []
        self.x: np.ndarray = np.array(x)
        self.baseline: np.ndarray = np.array(baseline)
    def add_line(self, name, vals, color=None):
        self.traces.append(go.Scatter(
            x=self.x,
            y=np.array(vals)-self.baseline,
            name=name,
            line=dict(color=color)))
    def add_secondary_line(self, name, vals, color=None):
        self.secondary_traces.append(go.Scatter(
            x=self.x,
            y=np.array(vals)-self.baseline,
            name=name,
            line=dict(color=color)))
    def add_dots(self, name, stuff, i, y, l, color, opacity):
        rgb = "220,0,0" if color == "red" \
        else "0,180,0" if color == "green" \
        else ""
        self.traces.append(go.Scatter(
            x=[self.x[i(s)] for s in stuff if i(s) is not None],
            y=[y(s)-self.baseline[i(s)] for s in stuff if i(s) is not None],
            mode="markers",
            line=dict(color=None if color is None else f"rgba({rgb},{opacity})", width=1),
            name=name,
            customdata=[l(s,self.x[i(s)],y(s)-self.baseline[i(s)]) for s in stuff if i(s) is not None],
            hovertemplate=f"{name}: %{{customdata}}"))
    def add_cross(self, name, stuff, i, y, l, color):
        self.traces.append(go.Scatter(
            x=[self.x[i(s)] for s in stuff if i(s) is not None],
            y=[y(s)-self.baseline[i(s)] for s in stuff if i(s) is not None],
            mode="markers",
            marker=dict(symbol="cross", color=color, size=8),
            name=name,
            customdata=[l(s,self.x[i(s)],y(s)-self.baseline[i(s)]) for s in stuff if i(s) is not None],
            hovertemplate=f"{name}: %{{customdata}}"))
    def add_arrows(self, name, stuff, i, y, l, direction):
        color = "red" if direction == "down" \
        else "green" if direction == "up" \
        else f"{1/0}"
        symbol = "triangle-down" if direction == "down" \
        else "triangle-up" if direction == "up" \
        else f"{1/0}"
        self.traces.append(go.Scatter(
            x=[self.x[i(s)] for s in stuff if i(s) is not None],
            y=[y(s)-self.baseline[i(s)] for s in stuff if i(s) is not None],
            mode="markers",
            marker=dict(symbol=symbol, color=color, size=8),
            name=name,
            customdata=[l(s,self.x[i(s)],y(s)-self.baseline[i(s)]) for s in stuff if i(s) is not None],
            hovertemplate=f"{name}: %{{customdata}}"),
        )
    def add_product_visualization(self, product, data: Round3Data):
        self.add_line(product, data.mid(product))
        for i in [1,2,3]:
            if 0:self.add_dots(f"{product}_ask{i}",
                stuff=data.askl(product,i),
                i=lambda b:b[0],
                y=lambda b:b[1],
                l=lambda s,x,y:f"ask{i}({x},{y},{s[2]})",
                color="red",
                opacity=0.6-0.1*i)
        for i in [3,2,1]:
            if 0:self.add_dots(f"{product}_bid{i}",
                stuff=data.bidl(product,i),
                i=lambda b:b[0],
                y=lambda b:b[1],
                l=lambda s,x,y:f"bid{i}({x},{y},{s[2]})",
                color="green",
                opacity=0.6-0.1*i)
        if 1:self.add_cross(f"{product}_bot_trades",
            stuff=data.bot_trades(product),
            i=lambda t:t.timestamp//100,
            y=lambda t:t.price,
            l=lambda s,x,y:f"({x},{y},{s.quantity})",
            color="purple")
        if 1:self.add_arrows(f"{product}_own_trades",
            stuff=data.own_buys(product),
            i=lambda t:t.timestamp//100,
            y=lambda t:t.price,
            l=lambda s,x,y:f"({x},{y},{s.quantity})",
            direction="up")
        if 1:self.add_arrows(f"{product}_own_trades",
            stuff=data.own_sells(product),
            i=lambda t:t.timestamp//100,
            y=lambda t:t.price,
            l=lambda s,x,y:f"({x},{y},{s.quantity})",
            direction="down")

class BigPicture:
    def __init__(self,rows,height,share_x=False):
        self.height=height
        self.fig = make_subplots(
            rows=rows,
            cols=1,
            shared_xaxes=share_x,vertical_spacing=0.01,
            specs=[[{"secondary_y": True}]]*rows)
    def add(self,pic,row):
        for trace in pic.traces:
            self.fig.add_trace(trace,row,1,False)
        for trace in pic.secondary_traces:
            self.fig.add_trace(trace,row,1,True)
    def show(self):
        self.fig.update_layout(
            height=self.height,
            hovermode="x",
            spikedistance=1,
            hoverdistance=1,
            margin=go.layout.Margin(l=0,r=0,b=0,t=0)
        )
        self.fig.update_xaxes(showspikes=True, spikesnap="cursor", spikemode="across", spikedash="solid")
        self.fig.update_yaxes(tickformat=",")
        self.fig.show()
    