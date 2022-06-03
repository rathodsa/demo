
from collections import Counter


def get_count(my_string):
    words = my_string.split()
    print(type(words))
    print(Counter(words))
    count = dict()
    for word in words:
        if word in count:
            count[word] += 1
        else:
            count[word] = 1
    return count


my_string = str(input("enter the string that you want the string occurance in: "))
print(get_count(my_string))