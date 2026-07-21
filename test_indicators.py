from app.indicators import supertrend

high = [
    48.70,
    48.72,
    48.90,
    48.87,
    48.82,
    49.05,
    49.20,
    49.35,
    49.50,
    49.40,
    49.60,
    49.75,
    49.80,
    49.95,
    50.10,
    50.30,
    50.20,
    50.40,
    50.60,
    50.80,
]

low = [
    48.20,
    48.30,
    48.50,
    48.45,
    48.40,
    48.70,
    48.80,
    49.00,
    49.15,
    49.05,
    49.20,
    49.40,
    49.45,
    49.60,
    49.75,
    49.90,
    49.80,
    50.00,
    50.25,
    50.50,
]

close = [
    48.50,
    48.60,
    48.70,
    48.60,
    48.75,
    48.95,
    49.05,
    49.20,
    49.35,
    49.25,
    49.50,
    49.60,
    49.70,
    49.85,
    50.00,
    50.10,
    50.00,
    50.30,
    50.50,
    50.70,
]

result = supertrend(high, low, close)

print("ATR")
print(result["atr"])

print()

print("Basic Upper")
print(result["basic_upper"])

print()

print("Basic Lower")
print(result["basic_lower"])

print()
print("Final Upper")
print(result["final_upper"])

print()
print("Final Lower")
print(result["final_lower"])

print()
print("SuperTrend")
print(result["supertrend"])

print()
print("Direction")
print(result["direction"])
