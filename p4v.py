from lib_data import Round3DataBacktest, Round3Data
from lib_plots import BigPicture, Picture, plotly_colors
from lib_signal import ma,smile_pred_impl_vol,smile_pred_price,moneyness,impl_vol,fit,pred,prem,delta
from p4 import Trader
data = Round3Data(cached=True)


K=5300
# product = data.V_product(K)
fig = BigPicture(3,1800,share_x=True)
pic = Picture(
    data.timestamps(),
    data.S()*1.9
)
pic.add_product_visualization(data.S2_product(), data)
pic.add_line("ask", [p[1] for p in data.askl(data.S2_product(), 1)])
pic.add_line("bid", [p[1] for p in data.bidl(data.S2_product(), 1)])
fig.add(pic,1)
pic = Picture(
    data.timestamps(),
    data.zeros()
)
pic.add_product_visualization(data.S_product(), data)
fig.add(pic,2)
pic = Picture(
    data.timestamps(),
    data.zeros()
)
pic.add_product_visualization(data.S2_product(), data)
pic.add_line("ask", [p[1] for p in data.askl(data.S2_product(), 1)])
pic.add_line("bid", [p[1] for p in data.bidl(data.S2_product(), 1)])
fig.add(pic,3)
# for Ki,K in enumerate([5000,5100,5200,5300,5400,5500]):
#     pic = Picture(
#         data.timestamps(),
#         data.zeros()
#     )
#     product = data.V_product(K)
#     pic.add_product_visualization(product, data)
#     fig.add(pic, Ki+2)
fig.show()