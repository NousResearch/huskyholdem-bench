import os
from config import RESULT_FILE

def extract_score():
    """Extract and print the average score from the game result file."""
    if not os.path.exists(RESULT_FILE):
        print("0")
        return
    
    try:
        with open(RESULT_FILE, 'r') as f:
            content = f.read()

        if "Total:" in content:
            lines = content.split('\n')
            for line in lines:
                if "Total:" in line:
                    try:
                        # Extract the number after "Total:" and before ","
                        score_part = line.split("Total:")[1]
                        score_str = score_part.split(",")[0].strip()
                        print(score_str)
                        return
                    except Exception:
                        continue
        
        print("0")
        
    except Exception as e:
        print("0")

if __name__ == "__main__":
    extract_score()