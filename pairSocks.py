from collections import Counter
def pairingSocks(n, ar):
    n = Counter(ar)
    return sum(i // 2 for i in n.values())



n = 9
ar=[10, 20, 20, 10, 10, 30, 50, 10, 20]
result = pairingSocks(n, ar)
print(result)