import unittest

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game.game import Game
from poker_type.game import PokerAction, PokerRound


class TestAddPlayer(unittest.TestCase):
    def test_add_no_player(self):
        game = Game(debug=True)
        self.assertEqual(game.players, [])
        self.assertEqual(game.active_players, [])

    def test_add_one_player(self):
        game = Game(debug=True)
        game.add_player(99)
        self.assertEqual(game.players, [99])
        self.assertEqual(game.active_players, [99])

    def test_add_mult_players(self):
        game = Game(debug=True)
        game.add_player(99)
        game.add_player(11)
        game.add_player(22)
        self.assertEqual(game.players, [99, 11, 22])
        self.assertEqual(game.active_players, [99, 11, 22])

class TestIsNextRound(unittest.TestCase):
    def test_player_still_playing_non_river(self):
        game = Game(debug=True)
        game.add_player(1)
        game.add_player(2)
        game.add_player(3)
        game.start_game()
        game.update_game(1, (PokerAction.FOLD, 0))
        game.update_game(2, (PokerAction.FOLD, 0))
        self.assertEqual(False, game.is_next_round())

    def test_all_acts_non_river_round_not_end(self):
        game = Game(debug=True)
        game.add_player(1)
        game.add_player(2)
        game.add_player(3)
        game.start_game()
        game.update_game(1, (PokerAction.FOLD, 0))
        game.update_game(2, (PokerAction.FOLD, 0))
        game.update_game(3, (PokerAction.FOLD, 0))
        self.assertEqual(False, game.is_next_round())

    def test_all_acts_non_river_round_end(self):
        game = Game(debug=True)
        game.add_player(1)
        game.add_player(2)
        game.add_player(3)
        game.start_game()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.update_game(2, (PokerAction.CHECK, 0))
        game.update_game(3, (PokerAction.CHECK, 0))
        game.end_round()
        self.assertEqual(True, game.is_next_round())

    def test_river(self):
        game = Game(debug=True)
        game.add_player(1)
        game.start_game()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        self.assertEqual(False, game.is_next_round())

class TestIsGameOver(unittest.TestCase):
    def test_unstarted(self):
        game = Game(debug=True)
        # game have not started yet
        self.assertEqual(True, game.is_game_over())

    def test_pre_flop(self):
        game = Game(debug=True)
        game.add_player(1)
        game.start_game()
        self.assertEqual(False, game.is_game_over())

    def test_flop(self):
        game = Game(debug=True)
        game.add_player(1)
        game.start_game()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        self.assertEqual(False, game.is_game_over())

    def test_turn(self):
        game = Game(debug=True)
        game.add_player(1)
        game.start_game()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        self.assertEqual(False, game.is_game_over())

    def test_river(self):
        game = Game(debug=True)
        game.add_player(1)
        game.start_game()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        self.assertEqual(False, game.is_game_over())

    def test_river_end_but_not_end_game(self):
        game = Game(debug=True)
        game.add_player(1)
        game.start_game()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        self.assertEqual(False, game.is_game_over())

    def test_end_game(self):
        game = Game(debug=True)
        game.add_player(1)
        game.start_game()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.end_game()
        self.assertEqual(True, game.is_game_over())

class TestGetCurrentRound(unittest.TestCase):
    def test_preflop(self):
        game = Game(debug=True)
        game.add_player(1)
        game.start_game()
        self.assertEqual(PokerRound.PREFLOP, game.get_current_round())

    def test_flop(self):
        game = Game(debug=True)
        game.add_player(1)
        game.start_game()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        self.assertEqual(PokerRound.FLOP, game.get_current_round())

    def test_turn(self):
        game = Game(debug=True)
        game.add_player(1)
        game.start_game()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        self.assertEqual(PokerRound.TURN, game.get_current_round())

    def test_river(self):
        game = Game(debug=True)
        game.add_player(1)
        game.start_game()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        self.assertEqual(PokerRound.RIVER, game.get_current_round())

class TestStartGame(unittest.TestCase):
    def test_not_started(self):
        game = Game(debug=True)
        game.add_player(1)
        self.assertEqual(-1, game.round_index)
        self.assertEqual(None, game.current_round)

    def test_start_with_one_player(self):
        game = Game(debug=True)
        game.add_player(1)
        game.start_game()
        self.assertEqual(0, game.round_index)
        self.assertEqual(PokerRound.PREFLOP, game.get_current_round())
        self.assertEqual(2, len(game.hands[1]))
        self.assertEqual(0, game.total_pot)
        self.assertEqual([], game.historical_pots)
        self.assertEqual({1: 0}, game.score)
        self.assertEqual({}, game.player_history)

    def test_start_with_mult_players(self):
        game = Game(debug=True)
        game.add_player(1)
        game.add_player(2)
        game.start_game()
        self.assertEqual(0, game.round_index)
        self.assertEqual(PokerRound.PREFLOP, game.get_current_round())
        self.assertEqual(2, len(game.hands[1]))
        self.assertEqual(2, len(game.hands[2]))
        self.assertEqual(0, game.total_pot)
        self.assertEqual([], game.historical_pots)
        self.assertEqual({1: 0, 2: 0}, game.score)
        self.assertEqual({}, game.player_history)

class TestUpdateGame(unittest.TestCase):
    def test_player_not_in_the_game(self):
        game = Game(debug=True)
        game.start_game()
        self.assertRaises(ValueError, game.update_game, 1, (PokerAction.CHECK, 0))

    def test_player_fold(self):
        game = Game(debug=True)
        game.add_player(1)
        game.add_player(2)
        game.start_game()
        game.update_game(1, (PokerAction.FOLD, 0))
        self.assertTrue(1 not in game.active_players)

class TestStartRound(unittest.TestCase):
    def test_start_flop(self):
        game = Game(debug=True)
        game.add_player(1)
        game.start_game()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        self.assertEqual(3, len(game.board))
        self.assertEqual(1, game.round_index)

    def test_start_turn(self):
        game = Game(debug=True)
        game.add_player(1)
        game.start_game()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        self.assertEqual(4, len(game.board))
        self.assertEqual(2, game.round_index)

    def test_start_river(self):
        game = Game(debug=True)
        game.add_player(1)
        game.start_game()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.CHECK, 0))
        self.assertEqual(5, len(game.board))
        self.assertEqual(3, game.round_index)

class TestPotDistribution(unittest.TestCase):
    def test_all_players_fold_except_one(self):
        """Test that when all players fold except one, that player wins the pot"""
        game = Game(debug=True)
        game.add_player(1)
        game.add_player(2)
        game.add_player(3)
        game.start_game()
        
        # Set up a scenario where players bet money in the first round
        game.update_game(1, (PokerAction.RAISE, 10))
        game.update_game(2, (PokerAction.CALL, 10))
        game.update_game(3, (PokerAction.CALL, 10))
        
        # End the first round
        game.end_round()
        
        # Start the next round
        game.start_round()
        
        # All players fold except player 1
        game.update_game(1, (PokerAction.CHECK, 0))  # Player 1 doesn't fold
        game.update_game(2, (PokerAction.FOLD, 0))   # Player 2 folds
        game.update_game(3, (PokerAction.FOLD, 0))   # Player 3 folds
        
        # End the game
        game.end_game()
        
        # Player 1 should win the pot (30 chips total)
        expected_score = {1: 20, 2: -10, 3: -10}  # Player 1 wins 20 (net gain), others lose their bets
        self.assertEqual(expected_score, game.score)
        
        # Verify zero-sum
        total_score = sum(game.score.values())
        self.assertEqual(0, total_score)


class TestScenarioBased(unittest.TestCase):
    def test_scenario_from_original_game_data(self):
        """Simulate a scenario similar to the original game data where only one player remains after folds."""
        # Player IDs from the original scenario
        player_ids = [215302037, 2247384581, 3630612293, 3651530891, 3705131898, 3950465666]
        game = Game(debug=True)
        for player_id in player_ids:
            game.add_player(player_id)
        game.start_game()

        # Simulate betting in the first round (similar to the original game)
        game.update_game(3651530891, (PokerAction.RAISE, 5))   # Small blind
        game.update_game(2247384581, (PokerAction.RAISE, 10))  # Big blind
        game.update_game(3705131898, (PokerAction.RAISE, 17))
        game.update_game(3630612293, (PokerAction.CALL, 17))
        game.update_game(3950465666, (PokerAction.RAISE, 1051))
        game.update_game(215302037, (PokerAction.FOLD, 0))
        game.update_game(3651530891, (PokerAction.FOLD, 0))
        game.update_game(2247384581, (PokerAction.FOLD, 0))
        game.update_game(3705131898, (PokerAction.RAISE, 1601))
        game.update_game(3630612293, (PokerAction.CALL, 1601))
        game.update_game(3950465666, (PokerAction.RAISE, 1216))
        game.update_game(3705131898, (PokerAction.RAISE, 4534))
        game.update_game(3630612293, (PokerAction.CALL, 4534))
        game.update_game(3950465666, (PokerAction.FOLD, 0))

        # End the first round
        game.end_round()
        # Start the second round (flop)
        game.start_round()
        # In the second round, all players fold except one
        game.update_game(3705131898, (PokerAction.FOLD, 0))   # Player folds
        game.update_game(3630612293, (PokerAction.CHECK, 0))  # Player doesn't fold
        # End the game
        game.end_game()

        # Only player 3630612293 should have a positive score, others negative or zero
        winners = {player: score for player, score in game.score.items() if score > 0}
        losers = {player: score for player, score in game.score.items() if score < 0}
        self.assertTrue(3630612293 in winners)
        self.assertTrue(all(score <= 0 for pid, score in game.score.items() if pid != 3630612293))
        # Zero-sum check
        self.assertEqual(sum(game.score.values()), 0)


if __name__ == '__main__':
    unittest.main()
