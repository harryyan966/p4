from lib_data import Round3DataBacktest
from lib_plots import BigPicture, Picture, plotly_colors
from lib_signal import ma,smile_pred_impl_vol,smile_pred_price,moneyness,impl_vol,fit,pred,prem,delta
from p4 import Trader,Ks
data = Round3DataBacktest(Trader(), cached=True)


# Ks = [5100,5200,5300,5400,5500]
fig = BigPicture(len(Ks)+2,300*len(Ks),share_x=True)
pic = Picture(
    data.timestamps(),
    # data.S()
    data.zeros()
)
pic.add_product_visualization(data.S_product(), data)
fig.add(pic,2)
pnlpic = Picture(
    data.timestamps(),
    data.zeros(),
)
for Ki,K in enumerate(Ks):
    product = data.V_product(K)
    pic = Picture(
        data.timestamps(),
        # data.mid(product)
        data.zeros()
    )
    pic.add_product_visualization(product, data)
    pnlpic.add_secondary_line(f"{K}_pos", data.pos(product))
    # pnlpic.add_secondary_line("delta", data.pos(product) * delta(data.S(),K,data.TTE(),sigma) + data.pos(data.S_product()))
    fig.add(pic, 3+Ki)
pnlpic.add_line("pnl", data.pnl)
pnlpic.add_secondary_line("S_pos", data.pos(data.S_product()))
sigma = 0.0125
fig.add(pnlpic,1)

# print("V_trades: ", len(data.own_buys(product)) +len(data.own_sells(product)))
# print("S_trades: ", len(data.own_buys(data.S_product())) +len(data.own_sells(data.S_product())))

fig.show()