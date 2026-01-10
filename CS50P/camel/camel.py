input = input("camelCase: ").strip()

output = ""

for char in input:
    if char.isupper():
        output += "_" + char.lower()
    else:
        output += char

print(output)
