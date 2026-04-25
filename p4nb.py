# K=5000
# data = Round3DataBacktest(Trader(), cached=True)
# fig = BigPicture(2,600,share_x=True)
# theos = [r.logs["iv_mean_reversion"][K] for r in data.reactions]
# pic = Picture(data.timestamps(),theos)
# pic.add_product_visualization(data.V_product(K), data)
# print(theos)
# pic.add_line("theo", theos)
# fig.add(pic,1)
# pic = Picture(data.timestamps(),data.zeros())
# pic.add_line("pnl", data.pnl)
# fig.add(pic,2)
# fig.show()





# fig = BigPicture(1,600,share_x=True)
# pic = Picture(data.timestamps(),data.S())
# pic.add_line("S", data.S())
# for i in [1,2,3]:
#     if 1:pic.add_dots(f"S_ask{i}",
#         stuff=data.askl(data.S_product(),i),
#         i=lambda b:b[0],
#         y=lambda b:b[1],
#         l=lambda s,x,y:f"ask{i}({x},{y})",
#         color="red",
#         opacity=0.6-0.1*i)
# for i in [3,2,1]:
#     if 1:pic.add_dots(f"S_bid{i}",
#         stuff=data.bidl(data.S_product(),i),
#         i=lambda b:b[0],
#         y=lambda b:b[1],
#         l=lambda s,x,y:f"bid{i}({x},{y})",
#         color="green",
#         opacity=0.6-0.1*i)
# if 1:pic.add_cross(f"S_bot_trades",
#     stuff=data.bot_trades(data.S_product()),
#     i=lambda t:t.timestamp//100,
#     y=lambda t:t.price,
#     l=lambda s,x,y:f"({x},{y})",
#     color="purple")
# fig.add(pic,1)
# fig.show()