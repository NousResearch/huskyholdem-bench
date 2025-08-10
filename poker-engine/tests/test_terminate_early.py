import unittest

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game.game import Game
from poker_type.game import PokerAction, PokerRound

class TestTerminateGameEarly(unittest.TestCase):
    def test_early_game_end_all_fold(self):
        game = Game(debug=True)
        game.add_player(1)
        game.add_player(2)
        game.start_game()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.update_game(2, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_round()
        game.update_game(1, (PokerAction.FOLD, 0))
        game.update_game(2, (PokerAction.FOLD, 0))
        game.end_round()
        self.assertEqual(True, game.is_game_over())

    def test_early_game_end_preflop_fold(self):
        game = Game(debug=True)
        game.add_player(1)
        game.add_player(2)
        game.start_game()
        game.update_game(1, (PokerAction.FOLD, 0))
        game.update_game(2, (PokerAction.FOLD, 0))
        game.end_round()
        self.assertEqual(True, game.is_game_over())

    def test_early_game_end_river_fold(self):
        game = Game(debug=True)
        game.add_player(1)
        game.add_player(2)
        game.start_game()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.update_game(2, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_game()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.update_game(2, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_game()
        game.update_game(1, (PokerAction.CHECK, 0))
        game.update_game(2, (PokerAction.CHECK, 0))
        game.end_round()
        game.start_game()
        game.update_game(1, (PokerAction.FOLD, 0))
        game.update_game(2, (PokerAction.FOLD, 0))
        game.end_round()
        self.assertEqual(True, game.is_game_over())


if __name__ == '__main__':
    unittest.main()
