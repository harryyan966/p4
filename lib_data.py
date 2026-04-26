from utils import *

class Round3Data:
    def __init__(self, cached):
        round = 3
        path = f"data_p4/round{round}"
        self.days = [
            round-3,
            round-2,
            round-1,
        ]
        self.states = get_trading_states_from_data(path,self.days,use_p3=False,use_cache=cached)
        self.cache = {}
    def cached(self,name,val):
        if name not in self.cache:
            self.cache[name] = val()
        return self.cache[name]
    def timestamps(self):
        return self.cached("timestamps", lambda:np.array([s.timestamp for s in self.states]))
    def zeros(self):
        return self.cached("zeros", lambda:np.zeros(len(self.timestamps())))
    def TTE(self):
        return self.cached("TTE", lambda:((8-min(self.days))-self.timestamps()/10000_00))
    def mid(self,product):
        return self.cached(f"mid({product})", lambda:np.array([get_wall_mid(s.order_depths.get(product, OrderDepth())) for s in self.states]))
    def pos(self,product):
        return self.cached(f"pos({product})", lambda:np.array([s.position.get(product,0) for s in self.states]))
    def S2_product(self):
        return "HYDROGEL_PACK"
    def S2(self):
        return self.mid(self.S2_product())
    def S_product(self):
        return "VELVETFRUIT_EXTRACT"
    def S(self):
        return self.mid(self.S_product())
    def bidl(self,product,l):
        def res(t,order_depth):
            b=sorted(order_depth.buy_orders.items())
            if len(b)<l:return None,None,None
            return t//100,b[l-1][0],b[l-1][1]
        return self.cached(f"bid{l}({product})", lambda:[res(s.timestamp,s.order_depths.get(product, OrderDepth())) for s in self.states])
    def askl(self,product,l):
        "timestamp,price,quantity"
        def res(t,order_depth):
            b=sorted(order_depth.sell_orders.items(),reverse=True)
            if len(b)<l:return None,None,None
            return t//100,b[l-1][0],-b[l-1][1]
        return self.cached(f"ask{l}({product})", lambda:[res(s.timestamp,s.order_depths.get(product, OrderDepth())) for s in self.states])
    def bot_trades(self,product):
        return self.cached(f"bot_trades({product})", lambda:[t for s in self.states for t in s.market_trades.get(product, [])])
    def own_buys(self,product):
        return self.cached(f"own_buys({product})", lambda:[t for s in self.states for t in s.own_trades.get(product, []) if t.buyer == "SUBMISSION"])
    def own_sells(self,product):
        return self.cached(f"own_sells({product})", lambda:[t for s in self.states for t in s.own_trades.get(product, []) if t.seller == "SUBMISSION"])
    def V(self,K):
        return self.mid(self.V_product(K))
    def V_product(self,K):
        return f"VEV_{K}"


class Round3DataBacktest(Round3Data):
    def __init__(self, trader, cached):
        super().__init__(cached)
        self.reactions = local_backtest(trader, self.states, use_p3=False)
        self.states = [s.input_state for s in self.reactions]
        self.pnl = [sum(pnl.values()) for pnl in get_pnls_from_reactions(self.reactions)]

class P3Round3Data:
    def __init__(self, cached):
        round = 3
        path = f"data_p3/round{round}"
        days = [2,3,4]
        self.states = get_trading_states_from_data(path,days,use_p3=True,use_cache=cached)
        self.cache = {}
    def cached(self,name,val):
        if name not in self.cache:
            self.cache[name] = val()
        return self.cache[name]
    def timestamps(self):
        return self.cached("timestamps", lambda:np.array([s.timestamp for s in self.states]))
    def zeros(self):
        return self.cached("zeros", lambda:np.zeros(len(self.timestamps())))
    def TTE(self):
        return self.cached("TTE", lambda:((8-3)-self.timestamps()/10000_00))
    def mid(self,product):
        return self.cached(f"mid({product})", lambda:np.array([get_wall_mid(s.order_depths.get(product, OrderDepth())) for s in self.states]))
    def pos(self,product):
        return self.cached(f"pos({product})", lambda:np.array([s.position.get(product,0) for s in self.states]))
    def S2_product(self):
        return "VOLCANIC_ROCK"
    def S2(self):
        return self.mid(self.S2_product())
    def S_product(self):
        return "VOLCANIC_ROCK"
    def S(self):
        return self.mid(self.S_product())
    def bidl(self,product,l):
        def res(t,order_depth):
            b=sorted(order_depth.buy_orders.items())
            if len(b)<l:return None,None,None
            return t//100,b[-l][0],b[-l][1]
        return self.cached(f"bid{l}({product})", lambda:[res(s.timestamp,s.order_depths.get(product, OrderDepth())) for s in self.states])
    def askl(self,product,l):
        def res(t,order_depth):
            b=sorted(order_depth.sell_orders.items())
            if len(b)<l:return None,None,None
            return t//100,b[l-1][0],-b[l-1][1]
        return self.cached(f"ask{l}({product})", lambda:[res(s.timestamp,s.order_depths.get(product, OrderDepth())) for s in self.states])
    def bot_trades(self,product):
        return self.cached(f"bot_trades({product})", lambda:[t for s in self.states for t in s.market_trades.get(product, [])])
    def own_buys(self,product):
        return self.cached(f"own_buys({product})", lambda:[t for s in self.states for t in s.own_trades.get(product, []) if t.buyer == "SUBMISSION"])
    def own_sells(self,product):
        return self.cached(f"own_sells({product})", lambda:[t for s in self.states for t in s.own_trades.get(product, []) if t.seller == "SUBMISSION"])
    def V(self,K):
        return self.mid(f"VOLCANIC_ROCK_VOUCHER_{K}")


