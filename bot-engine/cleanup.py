import os
from config import RESULT_FILE

def main():
    if os.path.exists(RESULT_FILE) and os.path.isfile(RESULT_FILE):
        with open(RESULT_FILE, 'w') as file:
            file.truncate(0)

if __name__ == "__main__":
    main()
