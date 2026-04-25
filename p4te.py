from utils import P4_LISTINGS
from p4 import Ks
from lib_data import Round3Data
from lib_plots import BigPicture, Picture
from lib_signal import ma, smile_theo
data = Round3Data(cached=True)
# products = P4_LISTINGS.keys()
products = [data.S_product(),data.S2_product()]
fig = BigPicture(2,800,share_x=True)
for pi,product in enumerate(products):
    # theo = smile_theo(data.S(),K,data.TTE(),a,b,c)
    if product.startswith("VEV_"):
        continue
    pic = Picture(data.timestamps(),data.zeros())
    pic.add_line(product, 
                 vals=data.mid(product))
    if 0:pic.add_line(f"ma_{product}", 
                 vals=ma(data.mid(product), 20))
    if 0:pic.add_secondary_line(f"position_{product}",
                           vals=data.pos(product))
    for i in [1,2,3]:
        if 0:pic.add_dots(f"{product}_bid{i}",
            stuff=data.bidl(product,i),
            i=lambda b:b[0],
            y=lambda b:b[2],
            l=lambda b:f"bid{i}({b[1]},{b[2]})",
            color="green",
            opacity=0.6-0.1*i)
        if 0:pic.add_dots(f"{product}_ask{i}",
            stuff=data.askl(product,i),
            i=lambda b:b[0],
            y=lambda b:b[2],
            l=lambda b:f"ask{i}({b[1]},{b[2]})",
            color="red",
            opacity=0.6-0.1*i)
    if 0:pic.add_cross(f"{product}_bot_trades",
        stuff=data.bot_trades(product),
        i=lambda t:t.timestamp//100,
        y=lambda t:t.price,
        l=lambda t:f"{t.price},{t.quantity}",
        color="purple")
    if 0:pic.add_arrows(f"{product}_own_buys",
        stuff=data.own_buys(product),
        i=lambda t:t.timestamp//100,
        y=lambda t:t.price,
        l=lambda t:f"{t.price},{t.quantity}",
        direction="up")
    if 0:pic.add_arrows(f"{product}_own_sells",
        stuff=data.own_sells(product),
        i=lambda t:t.timestamp//100,
        y=lambda t:t.price,
        l=lambda t:f"{t.price},{t.quantity}",
        direction="up")
    fig.add(pic,pi+1)
fig.show()
