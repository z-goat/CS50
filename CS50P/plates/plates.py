def main():
    plate = input("Plate: ")
    if is_valid(plate):
        print("Valid")
    else:
        print("Invalid")


def is_valid(s):
    if len(s) < 2 or len(s) > 6:
        return False
    if not s[0:2].isalpha():
        return False
    number_started = False
    for i in range(len(s)):
        if s[i].isdigit():
            if not number_started and s[i] == '0': 
                return False
            number_started = True
        elif number_started and s[i].isalpha():
            return False
        elif not s[i].isalnum():
            return False
    return True

if __name__ == "__main__":
    main()