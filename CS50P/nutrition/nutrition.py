fruits = {
    "apple": 130,
    "avocado": 50,
    "banana": 110,
    "blackberries": 60,
    "blueberries": 85,
    "cantaloupe": 50,
    "cherries": 100,
    "grapefruit": 60,
    "grapes": 90,
    "honeydew": 50,
    "kiwifruit": 90,
    "lemon": 15,
    "lime": 20,
    "nectarine": 60,
    "orange": 80,
    "papaya": 55,
    "peach": 60,
    "pear": 100,
    "pineapple": 50,
    "plums": 70,
    "raspberries": 65,
    "strawberries": 50,
    "sweet cherries": 100,
    "tangerine": 50,
    "watermelon": 80,
}

fruit = input("Item: ").strip().lower()

if fruit in fruits:
    print(f"Calories: {fruits[fruit]}")