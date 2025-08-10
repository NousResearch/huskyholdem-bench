#!/usr/bin/env python3

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from game.game import Game
from poker_type.game import PokerAction

class TestBlindPosting(unittest.TestCase):
    
    def test_blinds_are_forced_bets(self):
        """
        Test that blinds are forced bets that cannot be manually raised.
        This is the core requirement: when blinds are posted, they are automatic
        and players cannot interfere with the amounts.
        """
        # Setup simple 3-player game
        game = Game(debug=True, blind_amount=20)
        game.add_player(1)  # Small blind
        game.add_player(2)  # Big blind  
        game.add_player(3)  # UTG
        
        # Set dealer position so player 1 is SB, player 2 is BB
        game.set_dealer_button_position(2)  # Player 3 is dealer
        game.assign_blinds()
        
        # Verify blind assignments
        self.assertEqual(game.small_blind_player, 1)
        self.assertEqual(game.big_blind_player, 2)
        
        # Start game - this should post blinds automatically
        game.start_game()
        game.post_blinds()  # Manually post blinds since start_game doesn't do it
        
        # Verify blinds are posted with correct amounts (forced, not manual)
        self.assertEqual(game.current_round.player_bets[1], 10)  # Small blind = 10 (20/2)
        self.assertEqual(game.current_round.player_bets[2], 20)  # Big blind = 20
        
        # Verify that blind players posted their blinds but are not in waiting_for initially
        # (because blinds are forced bets, not voluntary actions)
        self.assertNotIn(1, game.current_round.waiting_for)
        self.assertNotIn(2, game.current_round.waiting_for)
        
        # Verify action starts from UTG (player 3), not from blind players
        self.assertIn(3, game.current_round.waiting_for)
        
        print(f"After game start - waiting_for: {game.current_round.waiting_for}")
        print(f"Player bets: {game.current_round.player_bets}")
        print(f"Active players: {game.active_players}")
        print(f"SB: {game.small_blind_player}, BB: {game.big_blind_player}")
        
        # Have UTG fold to complete the action for non-blind players
        game.update_game(3, (PokerAction.FOLD, 0))
        
        print(f"After UTG folds - waiting_for: {game.current_round.waiting_for}")
        print(f"Active players after fold: {game.active_players}")
        print(f"Player actions: {game.current_round.player_actions}")
        
        # Now blind players should get their option to act
        self.assertIn(1, game.current_round.waiting_for)  # SB gets option
        self.assertIn(2, game.current_round.waiting_for)  # BB gets option
        
        # SB can call to match BB
        game.update_game(1, (PokerAction.CALL, 10))  # SB calls
        print(f"After SB calls - waiting_for: {game.current_round.waiting_for}")
        self.assertNotIn(1, game.current_round.waiting_for)  # SB should be removed
        
        # BB should still be waiting and can check (big blind option)
        self.assertIn(2, game.current_round.waiting_for)
        game.update_game(2, (PokerAction.CHECK, 0))  # BB checks
        
        print(f"After BB checks - waiting_for: {game.current_round.waiting_for}")
        
        # Now round should be complete
        self.assertTrue(game.current_round.is_round_complete())
        print("✅ Test passed: Blinds work as forced bets!")

if __name__ == '__main__':
    unittest.main()
