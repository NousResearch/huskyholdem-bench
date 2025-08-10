import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.game import Game
from poker_type.game import PokerAction


class TestServerEndGameBug(unittest.TestCase):
    """Test the bug where server calls end_game() twice, causing issues with game state"""
    
    def test_double_end_game_call_consistency(self):
        """Test that calling end_game() twice doesn't change the scores"""
        game = Game(debug=False)
        game.add_player(1)
        game.add_player(2)
        game.add_player(3)
        game.start_game()
        
        # Create a scenario where everyone folds except one player
        game.update_game(1, (PokerAction.RAISE, 50))
        game.update_game(2, (PokerAction.CALL, 50))
        game.update_game(3, (PokerAction.CALL, 50))
        game.end_round()
        
        game.start_round()
        game.update_game(1, (PokerAction.RAISE, 30))
        game.update_game(2, (PokerAction.FOLD, 0))
        game.update_game(3, (PokerAction.FOLD, 0))
        
        # This should trigger the "everyone folded except one" scenario
        self.assertEqual(len(game.active_players), 1)
        
        # First end_game() call
        game.end_game()
        score_after_first = game.get_final_score().copy()
        
        # Simulate what the buggy server was doing
        player_money = {1: 1000 + score_after_first[1], 2: 1000 + score_after_first[2], 3: 1000 + score_after_first[3]}
        player_delta = score_after_first.copy()
        game.update_final_money_after_game(score_after_first, player_money, player_delta)
        
        # Second end_game() call (this was the bug)
        game.end_game()
        score_after_second = game.get_final_score()
        
        # Scores should be identical after both calls
        self.assertEqual(score_after_first, score_after_second)
        
        # Verify zero-sum property
        self.assertEqual(sum(score_after_second.values()), 0)
        
        # Player 1 should win: total pot = 150 + 30 = 180, player 1 paid 80, net = 100
        self.assertEqual(score_after_second[1], 100)
        self.assertEqual(score_after_second[2], -50)
        self.assertEqual(score_after_second[3], -50)

    def test_single_end_game_call_correctness(self):
        """Test that a single end_game() call produces correct results"""
        game = Game(debug=False)
        game.add_player(1)
        game.add_player(2)
        game.add_player(3)
        game.start_game()
        
        # Same scenario as above
        game.update_game(1, (PokerAction.RAISE, 50))
        game.update_game(2, (PokerAction.CALL, 50))
        game.update_game(3, (PokerAction.CALL, 50))
        game.end_round()
        
        game.start_round()
        game.update_game(1, (PokerAction.RAISE, 30))
        game.update_game(2, (PokerAction.FOLD, 0))
        game.update_game(3, (PokerAction.FOLD, 0))
        
        # Single end_game() call (the fixed behavior)
        game.end_game()
        score = game.get_final_score()
        
        # Verify correct scores
        self.assertEqual(score[1], 100)  # Winner gets 180 total - 80 paid = 100 net
        self.assertEqual(score[2], -50)  # Lost their 50
        self.assertEqual(score[3], -50)  # Lost their 50
        
        # Verify zero-sum
        self.assertEqual(sum(score.values()), 0)

    def test_fold_scenario_with_no_money_at_risk(self):
        """Test edge case where players fold without betting"""
        game = Game(debug=False)
        game.add_player(1)
        game.add_player(2)
        game.add_player(3)
        game.start_game()
        
        # Player 1 raises, others fold immediately
        game.update_game(1, (PokerAction.RAISE, 100))
        game.update_game(2, (PokerAction.FOLD, 0))
        game.update_game(3, (PokerAction.FOLD, 0))
        
        game.end_game()
        score = game.get_final_score()
        
        # Player 1 should get their money back (net 0)
        # Others should lose nothing (they didn't bet)
        self.assertEqual(score[1], 0)  # Gets back their 100
        self.assertEqual(score[2], 0)  # Didn't bet anything
        self.assertEqual(score[3], 0)  # Didn't bet anything
        
        # Verify zero-sum
        self.assertEqual(sum(score.values()), 0)

    def test_complex_multi_round_fold_scenario(self):
        """Test complex scenario with multiple rounds and folds"""
        game = Game(debug=False)
        game.add_player(1)
        game.add_player(2)
        game.add_player(3)
        game.add_player(4)
        game.start_game()
        
        # Round 1: Everyone bets
        game.update_game(1, (PokerAction.RAISE, 20))
        game.update_game(2, (PokerAction.CALL, 20))
        game.update_game(3, (PokerAction.CALL, 20))
        game.update_game(4, (PokerAction.CALL, 20))
        game.end_round()
        
        # Round 2: Some more betting, then folds
        game.start_round()
        game.update_game(1, (PokerAction.RAISE, 40))
        game.update_game(2, (PokerAction.CALL, 40))
        game.update_game(3, (PokerAction.FOLD, 0))
        game.update_game(4, (PokerAction.FOLD, 0))
        game.end_round()
        
        # Round 3: Final round, one player folds
        game.start_round()
        game.update_game(1, (PokerAction.RAISE, 50))
        game.update_game(2, (PokerAction.FOLD, 0))
        
        # Now only player 1 is left
        self.assertEqual(len(game.active_players), 1)
        
        game.end_game()
        score = game.get_final_score()
        
        # Total pot: 20*4 + 40*2 + 50 = 80 + 80 + 50 = 210
        # Player 1 paid: 20 + 40 + 50 = 110, net = 210 - 110 = 100
        # Player 2 paid: 20 + 40 = 60, net = -60
        # Player 3 paid: 20, net = -20
        # Player 4 paid: 20, net = -20
        
        self.assertEqual(score[1], 100)
        self.assertEqual(score[2], -60)
        self.assertEqual(score[3], -20)
        self.assertEqual(score[4], -20)
        
        # Verify zero-sum
        self.assertEqual(sum(score.values()), 0)


if __name__ == '__main__':
    unittest.main()
