#!/usr/bin/env python3

import unittest
import json
import tempfile
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from game.game import Game

class TestPlayerMoneyLogging(unittest.TestCase):
    """Test cases for player money logging in game JSON"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.game = Game(debug=False)
        self.players = [1001, 1002, 1003]
        self.initial_money = 10000
        self.player_starting_money = {1001: 10000, 1002: 9500, 1003: 10500}
        self.player_delta = {1001: 0, 1002: -500, 1003: 500}
        
        # Add players to game
        for player_id in self.players:
            self.game.add_player(player_id)
    
    def test_player_money_info_logging(self):
        """Test that player money information is correctly logged"""
        # Set player money information
        self.game.set_player_money_info(
            self.player_starting_money,
            self.player_delta,
            self.initial_money
        )
        
        # Start game (this creates the JSON log structure)
        self.game.start_game()
        
        # Check that player money information is in the JSON log
        self.assertIn('playerMoney', self.game.json_game_log)
        player_money_section = self.game.json_game_log['playerMoney']
        
        # Check initial amount
        self.assertEqual(player_money_section['initialAmount'], self.initial_money)
        
        # Check starting money
        self.assertIn('startingMoney', player_money_section)
        for player_id, money in self.player_starting_money.items():
            self.assertEqual(int(player_money_section['startingMoney'][str(player_id)]), money)
        
        # Check starting delta
        self.assertIn('startingDelta', player_money_section)
        for player_id, delta in self.player_delta.items():
            self.assertEqual(int(player_money_section['startingDelta'][str(player_id)]), delta)
    
    def test_final_money_info_logging(self):
        """Test that final money information is correctly logged after game ends"""
        # Set initial money information
        self.game.set_player_money_info(
            self.player_starting_money,
            self.player_delta,
            self.initial_money
        )
        
        # Start game
        self.game.start_game()
        
        # Simulate game scores
        game_scores = {1001: 100, 1002: -200, 1003: 100}
        
        # Update player_final_money to reflect the expected final money
        expected_final_money = {1001: 10100, 1002: 9300, 1003: 10600}
        for player_id, money in expected_final_money.items():
            self.game.player_final_money[player_id] = money
        
        # Set the scores before ending the game
        self.game.score = game_scores
        
        # End game (this should add final money information)
        self.game.end_game()
        
        # Check final money information
        player_money_section = self.game.json_game_log['playerMoney']
        
        # Check final money
        self.assertIn('finalMoney', player_money_section)
        for player_id, expected_money in expected_final_money.items():
            actual_money = int(player_money_section['finalMoney'][str(player_id)])
            self.assertEqual(actual_money, expected_money)
        
        # Check final delta (should be starting delta + game scores)
        self.assertIn('finalDelta', player_money_section)
        for player_id, score in game_scores.items():
            starting_delta = self.player_delta[player_id]
            expected_final_delta = starting_delta + score
            actual_final_delta = int(player_money_section['finalDelta'][str(player_id)])
            self.assertEqual(actual_final_delta, expected_final_delta)
        
        # Check game scores
        self.assertIn('gameScores', player_money_section)
        for player_id, score in game_scores.items():
            self.assertEqual(int(player_money_section['gameScores'][str(player_id)]), score)
        
        # Check this game delta
        self.assertIn('thisGameDelta', player_money_section)
        for player_id, score in game_scores.items():
            self.assertEqual(int(player_money_section['thisGameDelta'][str(player_id)]), score)
    
    def test_no_player_money_info(self):
        """Test that game still works without player money information"""
        # Start game without setting player money info
        self.game.start_game()
        
        # Should not have playerMoney section
        self.assertNotIn('playerMoney', self.game.json_game_log)
        
        # End game should still work
        self.game.score = {1001: 0, 1002: 0, 1003: 0}
        self.game.end_game()
        
        # Should have created playerMoney section with minimal info
        self.assertIn('playerMoney', self.game.json_game_log)
    
    def test_json_structure_completeness(self):
        """Test that the complete JSON structure is correct"""
        # Set player money information
        self.game.set_player_money_info(
            self.player_starting_money,
            self.player_delta,
            self.initial_money
        )
        
        # Start game
        self.game.start_game()
        
        # Set up expected final money and scores
        game_scores = {1001: 50, 1002: -100, 1003: 50}
        expected_final_money = {1001: 10050, 1002: 9400, 1003: 10550}
        
        # Update player_final_money to reflect the expected final money
        for player_id, money in expected_final_money.items():
            self.game.player_final_money[player_id] = money
        
        # Set the scores before ending the game
        self.game.score = game_scores
        
        # End game
        self.game.end_game()
        
        # Check complete structure
        expected_keys = ['initialAmount', 'startingMoney', 'startingDelta', 'finalMoney', 'finalDelta', 'gameScores', 'thisGameDelta']
        player_money_section = self.game.json_game_log['playerMoney']
        
        for key in expected_keys:
            self.assertIn(key, player_money_section, f"Missing key: {key}")
        
        # Verify final money calculation is correct
        for player_id, expected_money in expected_final_money.items():
            actual_money = int(player_money_section['finalMoney'][str(player_id)])
            self.assertEqual(actual_money, expected_money)
        
        # Verify final delta calculation is correct
        for player_id, score in game_scores.items():
            starting_delta = self.player_delta[player_id]
            expected_final_delta = starting_delta + score
            actual_final_delta = int(player_money_section['finalDelta'][str(player_id)])
            self.assertEqual(actual_final_delta, expected_final_delta)
        
        # Verify JSON is serializable
        json_str = json.dumps(self.game.json_game_log, indent=2)
        self.assertIsInstance(json_str, str)
        
        # Verify JSON can be parsed back
        parsed_json = json.loads(json_str)
        self.assertEqual(parsed_json['playerMoney']['initialAmount'], self.initial_money)

if __name__ == '__main__':
    unittest.main(verbosity=2) 