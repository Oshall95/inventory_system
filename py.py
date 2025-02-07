def draw_heart():
    name = " Baby Tastas "
    heart_width = 35
    heart_height = 6

    # Top of the heart
    print(" " * (heart_width // 2 - 3) + "♥   ♥   ♥   ♥")
    print(" " * (heart_width // 2 - 5) + "♥♥♥ ♥♥♥ ♥♥♥ ♥♥♥")

    # Upper curve
    for i in range(heart_height):
        spaces = " " * (heart_width // 2 - i * 2)
        line = "♥" * (4 + i * 4)
        print(spaces + line + spaces)

    # Center and bottom
    for i in range(heart_height, heart_height + 5):
        spaces = " " * (i - heart_height)
        if i == heart_height + 2:  # Add name in the middle
            print(spaces + "♥" + " " * (heart_width - 4) + "♥")
            print(spaces + "♥ " + name.center(heart_width - 4) + " ♥")
            print(spaces + "♥" + " " * (heart_width - 4) + "♥")
        else:
            line = "♥" * (heart_width - (i - heart_height) * 2)
            print(spaces + line)

draw_heart()
