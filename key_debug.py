import os

while True:
    print("about to read")
    b = os.read(0, 1)
    print(repr(b))
