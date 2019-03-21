words = ['INFORMATICS',
         'WINDOWS']
symbols = []
for word in words:
    symbols.append(set(list(word)))

both_sym = symbols[0] & symbols[1]

words_another = [
    'HISTORY',
    'GEOGRAPHY',
    'ARCHEOLOGY',
    'PROGRAMMING',
    'LINUX',
    'CODING',
    'MUTEX'
]
res = both_sym
for word in words_another:
    res = res - set(list(word))

print(res)
