#!/usr/bin/env python3

import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server import PokerEngineServer
from game.game import Game

from poker_type.game import PokerAction

class TestDealerRotationWithMoney(unittest.TestCase):
    """Test dealer button rotation considering players who can't afford blinds"""
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        self.server = PokerEngineServer(host='localhost', port=5003, num_players=4, debug=True)
        
        # Set up players: 1, 2, 3, 4 (player 2 can't afford blind)
        self.server.player_connections = {
            1: None,
            2: None,  # Can't afford blind
            3: None,
            4: None
        }
        
        self.server.player_money = {
            1: 1000,
            2: 3,     # Can't afford small blind (5)
            3: 7,     # Can afford small blind (5) but not big blind (10)
            4: 1000
        }
        
        self.server.player_delta = {1: 0, 2: 0, 3: 0, 4: 0}
        self.server.blind_amount = 10
        self.server.dealer_button_position = 0  # Start with player 1
        
        # Create a game instance for testing blind assignment
        self.game = Game(debug=True, blind_amount=10)
        for player_id in [1, 2, 3, 4]:
            self.game.add_player(player_id)
    
    def test_dealer_rotation_scenario(self):
        """Test the specific dealer rotation scenario:
        - Players: 1, 2, 3, 4 (2 can't afford small blind, 3 can't afford big blind)
        - Game 1: small=1, big=4
        - After rotation: small=4, big=1  
        - After rotation: small=1, big=4
        """
        
        print("\n=== Testing Dealer Rotation Scenario ===")
        
        # Game 1: Dealer at position 0 (player 1)
        print(f"\nGame 1 - Dealer position: {self.server.dealer_button_position}")
        self.game.set_dealer_button_position(self.server.dealer_button_position)
        self.game.assign_blinds_with_money_check(self.server.player_money, self.server.blind_amount)
        
        small_blind_1 = self.game.get_small_blind_player()
        big_blind_1 = self.game.get_big_blind_player()
        
        print(f"Small blind: {small_blind_1}, Big blind: {big_blind_1}")
        
        # Verify first game: small=1, big=4
        self.assertEqual(small_blind_1, 1, "First game: Small blind should be player 1")
        self.assertEqual(big_blind_1, 4, "First game: Big blind should be player 4")
        
        # Rotate dealer button
        print(f"\nRotating dealer button...")
        self.server.rotate_dealer_button()
        print(f"New dealer position: {self.server.dealer_button_position}")
        
        # Game 2: Dealer at new position
        self.game = Game(debug=True, blind_amount=10)
        for player_id in [1, 2, 3, 4]:
            self.game.add_player(player_id)
        
        self.game.set_dealer_button_position(self.server.dealer_button_position)
        self.game.assign_blinds_with_money_check(self.server.player_money, self.server.blind_amount)
        
        small_blind_2 = self.game.get_small_blind_player()
        big_blind_2 = self.game.get_big_blind_player()
        
        print(f"Small blind: {small_blind_2}, Big blind: {big_blind_2}")
        
        # Verify second game: small=4, big=1
        self.assertEqual(small_blind_2, 4, "Second game: Small blind should be player 4")
        self.assertEqual(big_blind_2, 1, "Second game: Big blind should be player 1")
        
        # Rotate dealer button again
        print(f"\nRotating dealer button again...")
        self.server.rotate_dealer_button()
        print(f"New dealer position: {self.server.dealer_button_position}")
        
        # Game 3: Dealer at new position
        self.game = Game(debug=True, blind_amount=10)
        for player_id in [1, 2, 3, 4]:
            self.game.add_player(player_id)
        
        self.game.set_dealer_button_position(self.server.dealer_button_position)
        self.game.assign_blinds_with_money_check(self.server.player_money, self.server.blind_amount)
        
        small_blind_3 = self.game.get_small_blind_player()
        big_blind_3 = self.game.get_big_blind_player()
        
        print(f"Small blind: {small_blind_3}, Big blind: {big_blind_3}")
        
        # Verify third game: small=1, big=4 (back to first pattern)
        self.assertEqual(small_blind_3, 1, "Third game: Small blind should be player 1")
        self.assertEqual(big_blind_3, 4, "Third game: Big blind should be player 4")
        
        print("\n=== All tests passed! ===")
    
    def test_player_2_never_gets_blind(self):
        """Test that player 2 (who can't afford small blind) and player 3 (who can't afford big blind) never get assigned as small or big blind"""
        
        print("\n=== Testing Players 2 and 3 Never Get Blind ===")
        
        # Test multiple rotations to ensure players 2 and 3 never get blind
        for game_num in range(10):
            print(f"\nGame {game_num + 1} - Dealer position: {self.server.dealer_button_position}")
            
            # Create new game instance
            self.game = Game(debug=True, blind_amount=10)
            for player_id in [1, 2, 3, 4]:
                self.game.add_player(player_id)
            
            self.game.set_dealer_button_position(self.server.dealer_button_position)
            self.game.assign_blinds_with_money_check(self.server.player_money, self.server.blind_amount)
            
            small_blind = self.game.get_small_blind_player()
            big_blind = self.game.get_big_blind_player()
            
            print(f"Small blind: {small_blind}, Big blind: {big_blind}")
            
            # Verify player 2 never gets blind (can't afford small blind)
            self.assertNotEqual(small_blind, 2, f"Game {game_num + 1}: Player 2 should not be small blind")
            self.assertNotEqual(big_blind, 2, f"Game {game_num + 1}: Player 2 should not be big blind")
            
            # Verify player 3 never gets blind (can't afford big blind)
            self.assertNotEqual(small_blind, 3, f"Game {game_num + 1}: Player 3 should not be small blind")
            self.assertNotEqual(big_blind, 3, f"Game {game_num + 1}: Player 3 should not be big blind")
            
            # Rotate for next game
            self.server.rotate_dealer_button()
        
        print("\n=== Players 2 and 3 never got blind assignment! ===")
    
    def test_dealer_button_only_rotates_among_affordable_players(self):
        """Test that dealer button only rotates among players who can afford the blind"""
        
        print("\n=== Testing Dealer Button Rotation Among Affordable Players ===")
        
        # Track which players become dealer
        dealer_players = set()
        
        for game_num in range(10):
            # Get current dealer player
            all_players = list(self.server.player_connections.keys())
            current_dealer_player = all_players[self.server.dealer_button_position % len(all_players)]
            dealer_players.add(current_dealer_player)
            
            print(f"Game {game_num + 1}: Dealer is player {current_dealer_player}")
            
            # Verify current dealer can afford big blind
            big_blind_amount = self.server.blind_amount
            can_afford = self.server.player_money[current_dealer_player] >= big_blind_amount
            self.assertTrue(can_afford, f"Game {game_num + 1}: Dealer player {current_dealer_player} should be able to afford big blind")
            
            # Rotate for next game
            self.server.rotate_dealer_button()
        
        # Verify only players who can afford big blind became dealer
        expected_dealers = {1, 4}  # Players 2 and 3 can't afford big blind
        self.assertEqual(dealer_players, expected_dealers, "Only players who can afford blind should become dealer")
        
        print(f"Dealer players: {dealer_players}")
        print("=== Only affordable players became dealer! ===")

if __name__ == "__main__":
    unittest.main(verbosity=2) 