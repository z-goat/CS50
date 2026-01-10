input = input("Input: ")

output = ""

for char in input:
    if char.lower() == "a" or char.lower() == "e" or char.lower() == "i" or char.lower() == "o" or char.lower() == "u":
        output += ""
    else:
        output += char

print(f"Output: {output}")
