from lib_data import Round3DataBacktest
from lib_plots import BigPicture, Picture, plotly_colors
from lib_signal import ma,smile_pred_impl_vol,smile_pred_price,moneyness,impl_vol,fit,pred,prem,delta
from p4 import Trader
data = Round3DataBacktest(Trader(), cached=True)


fig = BigPicture(2,300*2,share_x=True)
pic = Picture(
    data.timestamps(),
    # data.S()
    data.zeros()
)
pic.add_product_visualization(data.S2_product(), data)
fig.add(pic,2)
pnlpic = Picture(
    data.timestamps(),
    data.zeros(),
)
pnlpic.add_line("pnl", data.pnl)
pnlpic.add_secondary_line("S2_pos", data.pos(data.S2_product()))
fig.add(pnlpic,1)

# print("V_trades: ", len(data.own_buys(product)) +len(data.own_sells(product)))
# print("S_trades: ", len(data.own_buys(data.S_product())) +len(data.own_sells(data.S_product())))

fig.show()