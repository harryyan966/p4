import numpy as np
import matplotlib.pyplot as plt
######

def pft1():
    bid = np.array(range(670, 920))
    amt = (bid-670+4)//5
    pft = (920-bid) * amt
    plt.plot(bid, pft)
    plt.axvline(bid[pft.argmax()])
    plt.show()
    print(bid[pft.argmax()])

# pft1()

def pft2(mean: float):
    bid = np.array(range(670, 920))
    amt = np.maximum(0,(bid-790+4)//5)
    factor = np.minimum(1, ((920-mean)/(920-bid))**3)
    pft = (920-bid) * amt * factor
    # plt.plot(bid, pft)
    # plt.axvline(bid[pft.argmax()])
    # plt.axvline(mean, color="red")
    # plt.show()
    # print(mean, " -> ", bid[pft.argmax()])
    return pft[pft.argmax()]



def pft(mean: float):
    results = []
    max_pft = 0
    for bid1 in range(670,920):
        for bid2 in range(bid1,920):
            amt1 = (bid1-670+4)//5
            amt2 = max(0,(bid2-670+4)//5-amt1)
            factor = min(1,((920-mean)/(920-bid2))**3)
            pft1 = (920-bid1)*amt1
            pft2 = (920-bid2)*amt2*factor
            pft = pft1 + pft2
            if pft > max_pft:
                max_pft = pft
                results = [(bid1,bid2)]
            elif pft == max_pft:
                results.append((bid1,bid2))
    return (mean, max_pft, results)

results = []
for mean in range(670, 920):
    p = pft(mean)
    results.append(p)
    if mean == 836:
        print(p)
print(results)
fig, ax1 = plt.subplots()
ax2 = ax1.twinx()
ax1.plot([r[0] for r in results], [r[1] for r in results], color="green")
ax2.plot([r[0] for r in results], [r[2][0][0] for r in results])
ax2.plot([r[0] for r in results], [r[2][0][1] for r in results])
ax1.axvline(836)
plt.show()



# def hypo(mean: float):
#     results = []
#     pfts = []
#     for bid1 in range(670,920):
#         for bid2 in range(bid1,920):
#             amt1 = (bid1-670+4)//5
#             amt2 = max(0,(bid2-670+4)//5-amt1)
#             factor = min(1,((920-mean)/(920-bid2))**3)
#             pft1 = (920-bid1)*amt1
#             pft2 = (920-bid2)*amt2*factor
#             pft = pft1 + pft2
#             if pft > max_pft:
#                 max_pft = pft
#                 results = [(bid1,bid2)]
#             elif pft == max_pft:
#                 results.append((bid1,bid2))
#     return (mean, max_pft, results)