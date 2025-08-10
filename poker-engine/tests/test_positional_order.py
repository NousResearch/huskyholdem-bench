#!/usr/bin/env python3

import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from game.game import Game

class TestPositionalOrder(unittest.TestCase):
    """Test cases for positional ordering in poker games"""
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        self.game = Game(debug=False)
        # Standard 6-player game setup
        self.players_6 = [955063769, 1519405612, 3024546899, 3133671359, 3650021172, 3789843670]
        
    def test_6_player_preflop_order(self):
        """Test preflop ordering with 6 players"""
        # Add players
        for player_id in self.players_6:
            self.game.add_player(player_id)
        
        # Set dealer button at position 2 (3rd player)
        self.game.set_dealer_button_position(2)
        self.game.small_blind_player = 3024546899
        self.game.big_blind_player = 3133671359
        
        # Expect UTG to act first, then continue clockwise, with BB acting last
        preflop_order = self.game.get_preflop_order(self.players_6)
        
        # Small blind should act first
        self.assertEqual(preflop_order[4], self.game.small_blind_player,
                        "Small blind should act first in preflop")
        
        # Big blind should act last
        self.assertEqual(preflop_order[5], self.game.big_blind_player,
                        "Big blind should act last in preflop")
        
        # Verify all players are included
        self.assertEqual(len(preflop_order), 6, "All 6 players should be in preflop order")
        self.assertEqual(set(preflop_order), set(self.players_6), 
                        "All players should be included exactly once")
    
    def test_6_player_postflop_order(self):
        """Test post-flop ordering with 6 players"""
        # Add players
        for player_id in self.players_6:
            self.game.add_player(player_id)
        
        # Set dealer button at position 2 (3rd player)
        self.game.set_dealer_button_position(2)
        self.game.small_blind_player = 3024546899
        self.game.big_blind_player = 3133671359
        
        # Post-flop should start with small blind position
        postflop_order = self.game.get_positional_order(self.players_6)
        
        # Verify small blind acts first post-flop
        self.assertEqual(postflop_order[0], self.game.small_blind_player,
                        "Small blind should act first post-flop")
        
        # Verify all players are included
        self.assertEqual(len(postflop_order), 6, "All 6 players should be in post-flop order")
        self.assertEqual(set(postflop_order), set(self.players_6),
                        "All players should be included exactly once")
    
    def test_heads_up_ordering(self):
        """Test ordering with 2 players (heads-up)"""
        players_2 = [1519405612, 3789843670]
        
        # Add players
        for player_id in players_2:
            self.game.add_player(player_id)
        
        # Set dealer button at position 0
        self.game.set_dealer_button_position(0)
        self.game.small_blind_player = 1519405612
        self.game.big_blind_player = 3789843670
        
        
        # In heads-up: dealer is small blind, non-dealer is big blind
        # Preflop: small blind (dealer) acts first
        preflop_order = self.game.get_preflop_order(players_2)
        self.assertEqual(preflop_order[0], self.game.small_blind_player,
                        "Small blind should act first in heads-up preflop")
        
        # Post-flop: small blind acts first
        postflop_order = self.game.get_positional_order(players_2)
        self.assertEqual(postflop_order[0], self.game.small_blind_player,
                        "Small blind should act first in heads-up post-flop")
    
    def test_dealer_button_rotation(self):
        """Test that dealer button rotation affects ordering correctly"""
        # Add players
        for player_id in self.players_6:
            self.game.add_player(player_id)
        
        # Test different dealer positions
        for dealer_pos in range(6):
            self.game.set_dealer_button_position(dealer_pos)
            self.game.small_blind_player = self.players_6[dealer_pos]
            self.game.big_blind_player = self.players_6[(dealer_pos + 1) % 6]
            
            
            postflop_order = self.game.get_positional_order(self.players_6)
            
            # Verify small blind acts first in post-flop
            self.assertEqual(postflop_order[0], self.game.small_blind_player,
                            f"Small blind should act first post-flop with dealer at position {dealer_pos}")
            
            # Verify order is positional (clockwise from small blind)
            small_blind_index = self.players_6.index(self.game.small_blind_player)
            for i, player in enumerate(postflop_order):
                expected_player = self.players_6[(small_blind_index + i) % 6]
                self.assertEqual(player, expected_player,
                               f"Player at position {i} should be {expected_player}, got {player}")
    
    def test_partial_player_list(self):
        """Test ordering when some players have folded"""
        # Add all players
        for player_id in self.players_6:
            self.game.add_player(player_id)
        
        self.game.set_dealer_button_position(1)
        self.game.small_blind_player = self.players_6[1]
        self.game.big_blind_player = self.players_6[2]
        
        # Simulate 4 players remaining (2 folded)
        active_players = [1519405612, 3024546899, 3650021172, 3789843670]
        
        postflop_order = self.game.get_positional_order(active_players)
        
        # Verify only active players are included
        self.assertEqual(len(postflop_order), 4, "Only 4 active players should be in order")
        self.assertEqual(set(postflop_order), set(active_players),
                        "Only active players should be included")
        
        # Verify ordering is still positional
        # Find the first active player from small blind position
        small_blind_index = self.players_6.index(self.game.small_blind_player)
        first_active_from_sb = None
        for i in range(6):
            check_player = self.players_6[(small_blind_index + i) % 6]
            if check_player in active_players:
                first_active_from_sb = check_player
                break
        
        self.assertEqual(postflop_order[0], first_active_from_sb,
                        "First active player from small blind position should act first")
    
    def test_empty_player_list(self):
        """Test edge case with empty player list"""
        # Add players to game
        for player_id in self.players_6:
            self.game.add_player(player_id)
        
        self.game.set_dealer_button_position(0)
        self.game.assign_blinds()
        
        # Test with empty list
        empty_order = self.game.get_positional_order([])
        self.assertEqual(empty_order, [], "Empty player list should return empty order")
        
        preflop_empty = self.game.get_preflop_order([])
        self.assertEqual(preflop_empty, [], "Empty player list should return empty preflop order")
    
    def test_single_player(self):
        """Test edge case with single player"""
        single_player = [1519405612]
        
        # Add player
        self.game.add_player(single_player[0])
        self.game.set_dealer_button_position(0)
        
        # Single player should be returned as-is
        postflop_order = self.game.get_positional_order(single_player)
        self.assertEqual(postflop_order, single_player, "Single player should return as-is")
        
        preflop_order = self.game.get_preflop_order(single_player)
        self.assertEqual(preflop_order, single_player, "Single player should return as-is")
    
    def test_consistent_ordering(self):
        """Test that ordering is consistent across multiple calls"""
        # Add players
        for player_id in self.players_6:
            self.game.add_player(player_id)
        
        self.game.set_dealer_button_position(3)
        self.game.assign_blinds()
        
        # Multiple calls should return same order
        order1 = self.game.get_positional_order(self.players_6)
        order2 = self.game.get_positional_order(self.players_6)
        order3 = self.game.get_positional_order(self.players_6)
        
        self.assertEqual(order1, order2, "Multiple calls should return same order")
        self.assertEqual(order2, order3, "Multiple calls should return same order")
    
    def test_blind_assignment_correctness(self):
        """Test that blind assignments are correct for different dealer positions"""
        # Add players
        for player_id in self.players_6:
            self.game.add_player(player_id)
        
        for dealer_pos in range(6):
            self.game.set_dealer_button_position(dealer_pos)
            self.game.assign_blinds()
            
            # Small blind should be to the left of dealer
            expected_sb = self.players_6[(dealer_pos + 1) % 6]
            self.assertEqual(self.game.small_blind_player, expected_sb,
                            f"Small blind incorrect for dealer position {dealer_pos}")
            
            # Big blind should be to the left of small blind
            expected_bb = self.players_6[(dealer_pos + 2) % 6]
            self.assertEqual(self.game.big_blind_player, expected_bb,
                            f"Big blind incorrect for dealer position {dealer_pos}")

    def test_preflop_small_blind_first(self):
        """Test that small blind acts first in preflop betting"""
        # Add players
        for player_id in self.players_6:
            self.game.add_player(player_id)
        
        # Test different dealer positions
        for dealer_pos in range(6):
            self.game.set_dealer_button_position(dealer_pos)
            self.game.small_blind_player = self.players_6[dealer_pos]
            self.game.big_blind_player = self.players_6[(dealer_pos + 1) % 6]
            
            preflop_order = self.game.get_preflop_order(self.players_6)
            
            # Small blind should act 2nd last in preflop
            self.assertEqual(preflop_order[4], self.game.small_blind_player,
                            f"Small blind should act first in preflop with dealer at position {dealer_pos}")
            
            # Big blind should act last in preflop (position 5 in 6-player game)
            self.assertEqual(preflop_order[5], self.game.big_blind_player,
                            f"Big blind should act last in preflop with dealer at position {dealer_pos}")

if __name__ == '__main__':
    unittest.main(verbosity=2) 