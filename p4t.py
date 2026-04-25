from lib_data import Round3Data,P3Round3Data
from lib_plots import BigPicture, Picture, plotly_colors
from lib_signal import ma,smile_pred_impl_vol,smile_pred_price,moneyness,impl_vol,fit,pred,prem
from tqdm import tqdm
data = Round3Data(cached=True)
# Ks = [9500,9750,10000,10250,10500]
# Ks = [4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500]
Ks = [5000,5100,5200,5300,5400,5500]





fig = BigPicture(1,600,share_x=True)
pic = Picture(data.timestamps(),data.S())
pic.add_line("S", data.S())
for i in [1,2,3]:
    if 1:pic.add_dots(f"S_ask{i}",
        stuff=data.askl(data.S_product(),i),
        i=lambda b:b[0],
        y=lambda b:b[1],
        l=lambda s,x,y:f"ask{i}({x},{y})",
        color="red",
        opacity=0.6-0.1*i)
for i in [3,2,1]:
    if 1:pic.add_dots(f"S_bid{i}",
        stuff=data.bidl(data.S_product(),i),
        i=lambda b:b[0],
        y=lambda b:b[1],
        l=lambda s,x,y:f"bid{i}({x},{y})",
        color="green",
        opacity=0.6-0.1*i)
if 1:pic.add_cross(f"S_bot_trades",
    stuff=data.bot_trades(data.S_product()),
    i=lambda t:t.timestamp//100,
    y=lambda t:t.price,
    l=lambda s,x,y:f"({x},{y})",
    color="purple")
fig.add(pic,1)





# Kcs=dict(zip(Ks,plotly_colors[:len(Ks)]))
# ms = []
# sigmas = []
# for K in Ks:
#     prems = prem(data.V(K),data.S(),K)
#     V,S,TTE = data.V(K)[prems>0],data.S()[prems>0],data.TTE()[prems>0]
#     # if 5000<=K<=5500:
#     if K != 5400 and K != 5000:
#         ms += list(moneyness(S,K,TTE))
#         sigmas += list(impl_vol(V,S,K,TTE))
# a,b,c=fit(ms,sigmas,2)
# # a,b,c=[0,*fit(ms,sigmas,1)]
# # a,b,c=2.5487834457600465,0.011391714556033352,0.01231593477269045
# print(a,b,c,sep=",")







# fig = BigPicture(len(Ks),len(Ks)*200,share_x=True)
# for pi,K in enumerate(tqdm(Ks)):
#     if not 5000<=K<=5500:
#         continue
#     prems = prem(data.V(K),data.S(),K)
#     V,S,TTE = data.V(K)[prems>0],data.S()[prems>0],data.TTE()[prems>0]
#     sigma = impl_vol(V,S,K,TTE)
#     stuff = [(i,V[i],prems[i]) for i in range(len(sigma))]
#     theo = smile_theo(S,K,TTE,a,b,c)
#     pic = Picture(data.timestamps()[prems>0],theo)
#     pic.add_line(f"{K}", V)
#     for i in [1,2,3]:
#         if 1:pic.add_dots(f"{K}_ask{i}",
#             stuff=data.askl(data.V_product(K),i),
#             i=lambda b:b[0],
#             y=lambda b:b[1],
#             l=lambda b:f"ask{i}(p={b[1]},q={b[2]})",
#             color="red",
#             opacity=0.6-0.1*i)
#     for i in [3,2,1]:
#         if 1:pic.add_dots(f"{K}_bid{i}",
#             stuff=data.bidl(data.V_product(K),i),
#             i=lambda b:b[0],
#             y=lambda b:b[1],
#             l=lambda b:f"bid{i}(p={b[1]},q={b[2]})",
#             color="green",
#             opacity=0.6-0.1*i)
#     if 1:pic.add_cross(f"{K}_bot_trades",
#         stuff=data.bot_trades(data.V_product(K)),
#         i=lambda t:t.timestamp//100,
#         y=lambda t:t.price,
#         l=lambda t:f"{t.price},{t.quantity}",
#         color="purple")
#     fig.add(pic,pi+1)






# fig = BigPicture(len(Ks),len(Ks)*200,share_x=True)
# for i,K in enumerate(Ks):
#     prems = prem(data.V(K),data.S(),K)
#     V,S,TTE = data.V(K)[prems>0],data.S()[prems>0],data.TTE()[prems>0]
#     sigma = impl_vol(V,S,K,TTE)
#     stuff = [(i,V[i],prems[i]) for i in range(len(sigma))]
#     theo = smile_theo(S,K,TTE,a,b,c)
#     pic = Picture(data.timestamps()[prems>0],theo)
#     pic.add_cross(f"{K}",
#         stuff=stuff,
#         i=lambda p:p[0],
#         y=lambda p:p[1],
#         l=lambda p:f"t={p[0]},prem={p[2]}",
#         color=None
#     )
#     fig.add(pic,i+1)


"plot price and theo price"
# fig = BigPicture(len(Ks)+1,len(Ks)*200,share_x=True)
# pic = Picture(data.timestamps(),data.zeros())
# pic.add_line("S", data.S())
# fig.add(pic,1)
# for pi,K in enumerate(tqdm(Ks)):
#     prems = prem(data.V(K),data.S(),K)
#     V,S,TTE = data.V(K)[prems>0],data.S()[prems>0],data.TTE()[prems>0]
#     stuff = [(i,V[i],prems[i]) for i in range(len(V))]
#     theo = smile_pred_price(S,K,TTE,a,b,c)
#     pic = Picture(data.timestamps()[prems>0],theo)
#     pic.add_line(f"{K}", V)
#     for i in [1,2,3]:
#         if 1:pic.add_dots(f"{K}_ask{i}",
#             stuff=data.askl(data.V_product(K),i),
#             i=lambda b:b[0],
#             y=lambda b:b[1],
#             l=lambda s,x,y:f"ask{i}({x},{y})",
#             color="red",
#             opacity=0.6-0.1*i)
#     for i in [3,2,1]:
#         if 1:pic.add_dots(f"{K}_bid{i}",
#             stuff=data.bidl(data.V_product(K),i),
#             i=lambda b:b[0],
#             y=lambda b:b[1],
#             l=lambda s,x,y:f"bid{i}({x},{y})",
#             color="green",
#             opacity=0.6-0.1*i)
#     if 1:pic.add_cross(f"{K}_bot_trades",
#         stuff=data.bot_trades(data.V_product(K)),
#         i=lambda t:t.timestamp//100,
#         y=lambda t:t.price,
#         l=lambda s,x,y:f"({x},{y})",
#         color="purple")
#     pic.add_line(f"theo_{K}",theo)
#     fig.add(pic,pi+2)






"plot sigma and theo"
# fig = BigPicture(len(Ks)+1,len(Ks)*200,share_x=True)
# pic = Picture(data.timestamps(),data.zeros())
# pic.add_line("S", data.S())
# fig.add(pic,1)
# for i,K in enumerate(Ks):
#     prems = prem(data.V(K),data.S(),K)
#     V,S,TTE = data.V(K)[prems>0],data.S()[prems>0],data.TTE()[prems>0]
#     sigma = impl_vol(V,S,K,TTE)
#     stuff = [(i,sigma[i],prems[i]) for i in range(len(sigma))]
#     theo = smile_pred_impl_vol(S,K,TTE,a,b,c)
#     pic = Picture(data.timestamps()[prems>0],data.zeros()[prems>0])
#     pic.add_cross(f"{K}",
#         stuff=stuff,
#         i=lambda p:p[0],
#         y=lambda p:p[1],
#         l=lambda p:f"t={p[0]},prem={p[2]}",
#         color=Kcs[K]
#     )
#     pic.add_line(f"theo_{K}",theo)
#     fig.add(pic,i+2)













# fig = BigPicture(1,400,share_x=True)
# ms = []
# sigmas = []
# sms = []
# ssigmas = []
# for K in Ks:
#     prems = prem(data.V(K),data.S(),K)
#     V,S,TTE = data.V(K)[prems>0],data.S()[prems>0],data.TTE()[prems>0]
#     m = moneyness(S,K,TTE)
#     sigma = impl_vol(V,S,K,TTE)
#     stuff = [(i,sigma[i],prems[i]) for i in range(len(sigma))]
#     pic = Picture(m,[0]*len(m))
#     pic.add_cross(f"{K}",
#         stuff=stuff,
#         i=lambda p:p[0],
#         y=lambda p:p[1],
#         l=lambda p:f"t={p[0]},prem={p[2]}",
#         color=Kcs[K],
#     )
#     # if 5000<=K<=5500 and K != 5400:
#     if 1:
#         ms += list(m[[s[0] for s in stuff]])
#         sigmas += [s[1] for s in stuff]
#     # if 5000<=K<=5500:
#     if 1:
#         sms += list(m[[s[0] for s in stuff]])
#         ssigmas += [s[1] for s in stuff]
#         fig.add(pic,1)
# a,b,c=fit(ms,sigmas,2)
# print(a,b,c,sep=",")
# pic = Picture(sms,[0]*len(sms))
# pic.add_line(f"fitted_line",pred(sms,a,b,c))
# fig.add(pic,1)








# pic = Picture(data.timestamps(),data.zeros())
# pic.add_line(data.S_product(),data.S())
# fig.add(pic,2)













# for pi,product in enumerate(products):
#     # theo = smile_theo(data.S(),K,data.TTE(),a,b,c)
#     if product.startswith("VEV_"):
#         continue
#     pic = Picture(data.timestamps(),data.zeros())
#     pic.add_line(product, 
#                  vals=data.mid(product))
#     if 0:pic.add_line(f"ma_{product}", 
#                  vals=ma(data.mid(product), 20))
#     if 0:pic.add_secondary_line(f"position_{product}",
#                            vals=data.pos(product))
#     for i in [1,2,3]:
#         if 0:pic.add_dots(f"{product}_bid{i}",
#             stuff=data.bidl(product,i),
#             i=lambda b:b[0],
#             y=lambda b:b[2],
#             l=lambda b:f"bid{i}({b[1]},{b[2]})",
#             color="green",
#             opacity=0.6-0.1*i)
#         if 0:pic.add_dots(f"{product}_ask{i}",
#             stuff=data.askl(product,i),
#             i=lambda b:b[0],
#             y=lambda b:b[2],
#             l=lambda b:f"ask{i}({b[1]},{b[2]})",
#             color="red",
#             opacity=0.6-0.1*i)
#     if 0:pic.add_cross(f"{product}_bot_trades",
#         stuff=data.bot_trades(product),
#         i=lambda t:t.timestamp//100,
#         y=lambda t:t.price,
#         l=lambda t:f"{t.price},{t.quantity}",
#         color="purple")
#     if 0:pic.add_arrows(f"{product}_own_buys",
#         stuff=data.own_buys(product),
#         i=lambda t:t.timestamp//100,
#         y=lambda t:t.price,
#         l=lambda t:f"{t.price},{t.quantity}",
#         direction="up")
#     if 0:pic.add_arrows(f"{product}_own_sells",
#         stuff=data.own_sells(product),
#         i=lambda t:t.timestamp//100,
#         y=lambda t:t.price,
#         l=lambda t:f"{t.price},{t.quantity}",
#         direction="up")
fig.show()
