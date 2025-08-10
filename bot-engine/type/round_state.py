from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass
class RoundStateClient:
    round_num: int # The number of the current round
    round: str # The type of round (preflop, flop, turn, river)
    community_cards: List[str] # The community cards
    pot: int # The total pot
    current_player: List[int] # The ids of the current players
    current_bet: int # The current bet
    min_raise: int # The minimum raise amount
    max_raise: int # The maximum raise amount
    player_bets: Dict[str, int] # The bets of the players
    player_actions: Dict[str, str] # The actions of the players
    player_money: Dict[str, int] = None  # The money of the players
    side_pots: List[Dict[str, Any]] = None  # The side pots
    
    @classmethod
    def from_message(cls, message: Dict[str, Any]) -> 'RoundStateClient':
        """Create RoundStateClient from a message dictionary"""
        return cls(
            round_num=message['round_num'],
            round=message['round'],
            community_cards=message['community_cards'],
            pot=message['pot'],
            current_player=message['current_player'],
            current_bet=message['current_bet'],
            min_raise=message['min_raise'],
            max_raise=message['max_raise'],
            player_bets=message['player_bets'],
            player_actions=message['player_actions'],
            player_money=message.get('player_money'),
            side_pots=message.get('side_pots', [])
        )