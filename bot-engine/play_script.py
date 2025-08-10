# python play_script.py
# This script to test functionality of player class for our docker service

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from player import SimplePlayer
from type.round_state import RoundStateClient

def main():
    """
    A script to test the functionality of the SimplePlayer class.
    """
    
    # --- Test Initialization ---
    p = SimplePlayer()
    player_id = 1
    p.set_id(player_id)

    # --- Test on_start ---
    p.on_start(
        starting_chips=1000, 
        player_hands=["As", "Kd"], 
        blind_amount=10, 
        big_blind_player_id=2, 
        small_blind_player_id=1, 
        all_players=[1, 2, 3]
    )

    # --- Create a sample round state for testing ---
    round_state_data = {
        "round_num": 1,
        "round": "PREFLOP",
        "community_cards": [],
        "pot": 30,
        "current_player": [player_id],
        "current_bet": 20,
        "min_raise": 20,
        "max_raise": 980,
        "player_bets": {str(player_id): 10, "2": 20, "3": 0},
        "player_actions": {str(player_id): "RAISE", "2": "RAISE", "3": "WAIT"},
        "player_money": {str(player_id): 990, "2": 980, "3": 1000},
        "side_pots": []
    }
    round_state = RoundStateClient.from_message(round_state_data)
    
    # --- Test on_round_start ---
    p.on_round_start(round_state, 990)

    # --- Test get_action ---
    _ , _ = p.get_action(round_state, 990)

    # --- Test on_end_round ---
    p.on_end_round(round_state, 980)

    # --- Test on_end_game ---
    p.on_end_game(
        round_state=round_state, 
        player_score=50, 
        all_scores={1: 50, 2: -25, 3: -25},
        active_players_hands={1: ["As", "Kd"], 2: ["7h", "8h"]}
    )
    


if __name__ == "__main__":
    main()
