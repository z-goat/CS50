amount_due = 50

while amount_due > 0:
    print(f"Amount due: {amount_due}")
    coin = int(input("Insert coin: "))
    if coin in [25, 10, 5]:
        amount_due -= coin
    else:
        continue

change = abs(amount_due)

print(f"Change owed: {change}")
