import os
from config import OUTPUT_GAME_RESULT_FILE

def main():
    if os.path.exists(OUTPUT_GAME_RESULT_FILE) and os.path.isfile(OUTPUT_GAME_RESULT_FILE):
        with open(OUTPUT_GAME_RESULT_FILE, 'w') as file:
            file.truncate(0)

if __name__ == "__main__":
    main()
