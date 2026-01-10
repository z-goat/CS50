import sys

def main():
    time = input("What time is it? ")

    processed_time = convert(time)

    if 7.0 <= processed_time <= 8.0:
        print("breakfast time")
    elif 12.0 <= processed_time <= 13.0:
        print("lunch time")
    elif 18.0 <= processed_time <= 19.0:
        print("dinner time")
    else:
        sys.exit()

def convert(time):
    hours, minutes = time.split(":")
    hours = float(hours)
    minutes = float(minutes)
    return hours + (minutes / 60)

if __name__ == "__main__":
    main()
