calculation = input("Expression: ").strip().lower()

x, y, z = calculation.split(" ")

if y == "+":
    result = float(x) + float(z)
elif y == "-":
    result = float(x) - float(z)
elif y == "*":
    result = float(x) * float(z)
elif y == "/":
    result = float(x) / float(z)

print(f"{result}")
