def countingValleys(steps, path):
    current_steps = 0
    count = 0
    for i in range(steps):
        if path[i] == 'U':
            current_steps += 1
        elif path[i] == 'D':
            current_steps -= 1
            if current_steps == -1:
                count += 1
    return count


steps = 8
path = 'UDDDUDUU'
result = countingValleys(steps, path)
print(result)