from lib_data import Round3DataBacktest
from lib_plots import BigPicture, Picture, plotly_colors
from lib_signal import ma,smile_pred_impl_vol,smile_pred_price,moneyness,impl_vol,fit,pred,prem
from p4 import Trader
data = Round3DataBacktest(Trader(), cached=True)


# K=5300
# product = data.V_product(K)
product = data.S2_product()
fig = BigPicture(3,900,share_x=True)
pic = Picture(
    data.timestamps(),
    data.zeros()
    # ma(data.S2(), 4000)
)
pic.add_product_visualization(product, data)
fig.add(pic,1)
pic = Picture(
    data.timestamps(),
    # data.zeros(),
    data.S2()
    # ma(data.S2(), 4000)
)
pic.add_product_visualization(data.S_product(), data)
fig.add(pic,2)
pic = Picture(data.timestamps(),data.zeros())
pic.add_line("pnl", data.pnl)
pic.add_secondary_line("pos", data.pos(product))
fig.add(pic,3)

print(len(data.own_buys(product)))
print(len(data.own_sells(product)))

fig.show()