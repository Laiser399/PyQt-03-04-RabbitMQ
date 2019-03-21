import math

p = int(input())
p_2 = p * p

res = []
m = 1
while True:
    print(m)
    n = math.sqrt(p + m*m)
    if n <= m:
        break
    k = 2 * n * p
    gip = math.sqrt(k * k + p_2)
    if (k == int(k)) and (gip == int(gip)):
        res.append(gip)
    m += 1

print(res)