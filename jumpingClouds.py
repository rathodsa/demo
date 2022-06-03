
def jumpingCould(c):
    count = 0
    i = 0
    for i in range(7):
        print(i)
        if c[i] == 0:
            count += 1
        elif c[i] == 1:
            count -= 1
    return count

c = [0,0,1,0,0,1,0]
result = jumpingCould(c)
print(result)