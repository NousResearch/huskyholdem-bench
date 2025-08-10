import json
import numpy as np
from collections import defaultdict

def analyze_poker_log(log_file_path):
    with open(log_file_path, 'r') as file:
        data = json.load(file)
    
    action_scores = {
        'FOLD': -1,
        'CALL': -1,
        'CHECK': -1,
        'RAISE': 1,
        'BET': 1
    }
    player_actions = defaultdict(list)
    player_hand_avg_scores = defaultdict(list)
    
    rounds = data.get('game_data', {}).get('rounds', {})
    
    hand_scores = defaultdict(list)
    action_counts = defaultdict(lambda: defaultdict(int))
    
    for round_key, round_data in rounds.items():
        action_sequence = round_data.get('action_sequence', [])
        for action_entry in action_sequence:
            action = action_entry.get('action')
            player = str(action_entry.get('player'))
            if action and player:
                act_upper = action.upper()
                player_actions[player].append(act_upper)
                score = action_scores.get(act_upper, 0)
                hand_scores[player].append(score)
                action_counts[player][act_upper] += 1
    
    results = {}
    for player, actions in player_actions.items():
        total_actions = len(actions)
        if total_actions == 0:
            continue
        
        known_actions = ['FOLD', 'CALL', 'CHECK', 'RAISE', 'BET']
        action_rates = {act: action_counts[player][act] / total_actions for act in known_actions}
        other_count = total_actions - sum(action_counts[player][act] for act in known_actions)
        action_rates['OTHER'] = other_count / total_actions
        
        if hand_scores[player]:
            hand_avg_score = np.mean(hand_scores[player])
            player_hand_avg_scores[player].append(hand_avg_score)
        
        variance_behavior = np.var(player_hand_avg_scores[player]) if len(player_hand_avg_scores[player]) > 1 else 0.0
        
        results[player] = {
            'variance_behavior': variance_behavior,
            'action_rates': action_rates
        }
    
    return results

if __name__ == "__main__":
    log_path = 'example.json'
    metrics = analyze_poker_log(log_path)
    print(json.dumps(metrics, indent=4))
