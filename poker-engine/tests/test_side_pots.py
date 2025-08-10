import unittest
import sys
import os

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.game import Game
from poker_type.game import PokerAction
import eval7


class TestSidePots(unittest.TestCase):
    
    def test_simple_side_pot_scenario_with_scoring(self):
        """Test a simple side pot scenario with one all-in player and score calculation"""
        game = Game(debug=True)
        
        # Add three players
        game.add_player(1)
        game.add_player(2) 
        game.add_player(3)
        
        game.start_game()
        
        # Set specific hands for predictable results
        # Player 1 gets pair of Aces (strong hand)
        # Player 2 gets pair of Kings  
        # Player 3 gets high card
        game.hands[1] = [eval7.Card("As"), eval7.Card("Ad")]
        game.hands[2] = [eval7.Card("Ks"), eval7.Card("Kd")]
        game.hands[3] = [eval7.Card("Qh"), eval7.Card("Jc")]
        
        # Set a board
        game.board = [eval7.Card("2h"), eval7.Card("3s"), eval7.Card("4d"), eval7.Card("7c"), eval7.Card("9h")]
        
        # Player 1 goes all-in for 50
        game.update_game(1, (PokerAction.ALL_IN, 50))
        
        # Player 2 raises to 100  
        game.update_game(2, (PokerAction.RAISE, 100))
        
        # Player 3 calls 100
        game.update_game(3, (PokerAction.CALL, 100))
        
        # Check that side pots are created correctly
        self.assertEqual(len(game.current_round.pots), 2)
        
        # Main pot should be 150 (50 from each player)
        main_pot = game.current_round.pots[0]
        self.assertEqual(main_pot.amount, 150)
        self.assertEqual(main_pot.eligible_players, {1, 2, 3})
        
        # Side pot should be 100 (50 each from players 2 and 3)  
        side_pot = game.current_round.pots[1]
        self.assertEqual(side_pot.amount, 100)
        self.assertEqual(side_pot.eligible_players, {2, 3})
        
        print(f"Main pot: {main_pot.amount} chips, eligible: {main_pot.eligible_players}")
        print(f"Side pot: {side_pot.amount} chips, eligible: {side_pot.eligible_players}")
        
        # End the round and game to calculate scores
        game.end_round()
        game.end_game()
        
        # Player 1 should win main pot (150) with pair of Aces
        # Player 2 should win side pot (100) with pair of Kings vs Player 3's high card
        # Verify final scores: Player 1: 150-50=100, Player 2: 100-100=0, Player 3: 0-100=-100
        
        print(f"Final scores: {game.score}")
        self.assertEqual(game.score[1], 100)  # Won main pot, paid 50
        self.assertEqual(game.score[2], 0)    # Won side pot, paid 100  
        self.assertEqual(game.score[3], -100) # Won nothing, paid 100
        
        # Verify zero-sum
        self.assertEqual(sum(game.score.values()), 0)
    
    def test_multiple_side_pots_with_scoring(self):
        """Test scenario with multiple all-in players creating multiple side pots with score calculation"""
        game = Game(debug=True)
        
        # Add four players
        game.add_player(1)
        game.add_player(2)
        game.add_player(3)
        game.add_player(4)
        
        game.start_game()
        
        # Set specific hands for predictable results
        # Player 1: Pair of Aces (strongest)
        # Player 2: Pair of Kings 
        # Player 3: Pair of Queens
        # Player 4: High card Jack (weakest)
        game.hands[1] = [eval7.Card("As"), eval7.Card("Ad")]
        game.hands[2] = [eval7.Card("Ks"), eval7.Card("Kd")]
        game.hands[3] = [eval7.Card("Qs"), eval7.Card("Qd")]
        game.hands[4] = [eval7.Card("Jh"), eval7.Card("Tc")]
        
        # Set a board with no pairs/straights/flushes to keep hands predictable
        game.board = [eval7.Card("2h"), eval7.Card("3s"), eval7.Card("4d"), eval7.Card("7c"), eval7.Card("9h")]
        
        # Player 1 goes all-in for 30
        game.update_game(1, (PokerAction.ALL_IN, 30))
        
        # Player 2 goes all-in for 60 
        game.update_game(2, (PokerAction.ALL_IN, 60))
        
        # Player 3 goes all-in for 90
        game.update_game(3, (PokerAction.ALL_IN, 90))
        
        # Player 4 calls 90
        game.update_game(4, (PokerAction.CALL, 90))
        
        # Should create 3 pots
        self.assertEqual(len(game.current_round.pots), 3)
        
        # First pot: 30 * 4 = 120, all players eligible
        pot1 = game.current_round.pots[0]
        self.assertEqual(pot1.amount, 120)
        self.assertEqual(pot1.eligible_players, {1, 2, 3, 4})
        
        # Second pot: 30 * 3 = 90, players 2,3,4 eligible
        pot2 = game.current_round.pots[1]
        self.assertEqual(pot2.amount, 90)
        self.assertEqual(pot2.eligible_players, {2, 3, 4})
        
        # Third pot: 30 * 2 = 60, players 3,4 eligible  
        pot3 = game.current_round.pots[2]
        self.assertEqual(pot3.amount, 60)
        self.assertEqual(pot3.eligible_players, {3, 4})
        
        print(f"Pot 1: {pot1.amount} chips, eligible: {pot1.eligible_players}")
        print(f"Pot 2: {pot2.amount} chips, eligible: {pot2.eligible_players}")
        print(f"Pot 3: {pot3.amount} chips, eligible: {pot3.eligible_players}")
        
        # End the round and game to calculate scores
        game.end_round()
        game.end_game()
        
        # Expected winners:
        # Pot 1 (120): Player 1 wins with Aces
        # Pot 2 (90): Player 2 wins with Kings (among players 2,3,4)
        # Pot 3 (60): Player 3 wins with Queens (among players 3,4)
        
        print(f"Final scores: {game.score}")
        
        # Player 1: wins 120, paid 30 = +90
        # Player 2: wins 90, paid 60 = +30
        # Player 3: wins 60, paid 90 = -30
        # Player 4: wins 0, paid 90 = -90
        
        self.assertEqual(game.score[1], 90)   # Won pot 1
        self.assertEqual(game.score[2], 30)   # Won pot 2
        self.assertEqual(game.score[3], -30)  # Won pot 3
        self.assertEqual(game.score[4], -90)  # Won nothing
        
        # Verify zero-sum
        self.assertEqual(sum(game.score.values()), 0)
    
    def test_no_side_pots_equal_bets_with_scoring(self):
        """Test that no side pots are created when all players bet equally, with score calculation"""
        game = Game(debug=True)
        
        game.add_player(1)
        game.add_player(2)
        game.add_player(3)
        
        game.start_game()
        
        # Set hands - Player 2 has the best hand
        game.hands[1] = [eval7.Card("7s"), eval7.Card("3d")]  # Weak hand
        game.hands[2] = [eval7.Card("As"), eval7.Card("Ad")]  # Pair of Aces (best hand)
        game.hands[3] = [eval7.Card("9h"), eval7.Card("8c")]  # High card
        
        # Set a board that doesn't help anyone make straights/flushes
        game.board = [eval7.Card("2h"), eval7.Card("4s"), eval7.Card("6d"), eval7.Card("Jc"), eval7.Card("Kh")]
        
        # All players bet the same amount
        game.update_game(1, (PokerAction.RAISE, 50))
        game.update_game(2, (PokerAction.CALL, 50))
        game.update_game(3, (PokerAction.CALL, 50))
        
        # Should only have one pot
        self.assertEqual(len(game.current_round.pots), 1)
        self.assertEqual(game.current_round.pots[0].amount, 150)
        self.assertEqual(game.current_round.pots[0].eligible_players, {1, 2, 3})
        
        # End the round and game to calculate scores
        game.end_round()
        game.end_game()
        
        # Player 2 should win the entire pot with pair of Aces
        print(f"Final scores: {game.score}")
        self.assertEqual(game.score[1], -50)  # Lost bet
        self.assertEqual(game.score[2], 100)  # Won pot minus bet: 150-50=100
        self.assertEqual(game.score[3], -50)  # Lost bet
        
        # Verify zero-sum
        self.assertEqual(sum(game.score.values()), 0)

    def test_side_pots_all_in_lose_some_money(self):
        """Test that side pots are created when all players go all-in, and some players lose money"""
        game = Game(debug=True)
        
        game.add_player(1)
        game.add_player(2)

        game.start_game()
        
        # Set hands - Player 2 has the best hand
        game.hands[1] = [eval7.Card("7s"), eval7.Card("3d")]  # Weak hand
        game.hands[2] = [eval7.Card("As"), eval7.Card("Ad")]  # Pair of Aces (best hand)
        
        # Set a board that doesn't help anyone make straights/flushes
        game.board = [eval7.Card("2h"), eval7.Card("4s"), eval7.Card("6d"), eval7.Card("Jc"), eval7.Card("Kh")]

        # Player 1 goes all-in for 1000
        game.update_game(1, (PokerAction.ALL_IN, 24786))
        
        # Player 2 goes all-in for 50
        game.update_game(2, (PokerAction.ALL_IN, 7748))

        # Should create 2 pots
        self.assertEqual(len(game.current_round.pots), 2)
        # End the round and game to calculate scores
        game.end_round()
        game.end_game()
        
        # Player 2 should win the entire pot with pair of Aces
        print(f"Final scores: {game.score}")
        self.assertEqual(game.score[1], -7748)  # Lost bet
        self.assertEqual(game.score[2], 7748)  # Won pot minus bet: 150-50=100

    def test_all_in_win_limit_bug(self):
        """Test the specific bug where a player wins more than they should based on their all-in amount"""
        game = Game(debug=True)
        
        game.add_player(1)  # peak (smaller all-in)
        game.add_player(2)  # elise03 (larger all-in)

        game.start_game()
        
        # Set hands - Player 1 has the best hand (should win)
        game.hands[1] = [eval7.Card("As"), eval7.Card("Ad")]  # Pair of Aces (best hand)
        game.hands[2] = [eval7.Card("7s"), eval7.Card("3d")]  # Weak hand
        
        # Set a board that doesn't help anyone make straights/flushes
        game.board = [eval7.Card("2h"), eval7.Card("4s"), eval7.Card("6d"), eval7.Card("Jc"), eval7.Card("Kh")]

        # Player 1 (peak) goes all-in for 7748
        game.update_game(1, (PokerAction.ALL_IN, 7748))
        
        # Player 2 (elise03) goes all-in for 24786
        game.update_game(2, (PokerAction.ALL_IN, 24786))

        # Should create 2 pots
        self.assertEqual(len(game.current_round.pots), 2)
        
        # End the round and game to calculate scores
        game.end_round()
        game.end_game()
        
        # Player 1 should win, but can only win up to 2 * 7748 = 15496 chips
        # (their all-in amount from each player)
        print(f"Final scores: {game.score}")
        print(f"Player 1 bet: 7748, should win max: {7748 * 2}")
        print(f"Player 2 bet: 24786, should lose max: {7748 * 2}")
        
        # Player 1 should win at most 15496 chips (2 * their all-in amount)
        # Player 2 should lose at most 15496 chips
        self.assertLessEqual(game.score[1], 7748)  # Should win at most their all-in amount
        self.assertGreaterEqual(game.score[2], -15496)  # Should lose at most 2 * opponent's all-in amount
        
        # Verify zero-sum
        self.assertEqual(sum(game.score.values()), 0)

    def test_multiple_rounds_all_in_scenario(self):
        """Test the actual game scenario with multiple rounds and cumulative scoring"""
        game = Game(debug=True)
        
        game.add_player(1)  # peak
        game.add_player(2)  # elise03

        game.start_game()
        
        # Set hands - Player 1 has the best hand throughout
        game.hands[1] = [eval7.Card("As"), eval7.Card("Ad")]  # Pair of Aces (best hand)
        game.hands[2] = [eval7.Card("7s"), eval7.Card("3d")]  # Weak hand
        
        # Set a board that doesn't help anyone make straights/flushes
        game.board = [eval7.Card("2h"), eval7.Card("4s"), eval7.Card("6d"), eval7.Card("Jc"), eval7.Card("Kh")]

        # Round 0: Initial betting
        game.update_game(1, (PokerAction.ALL_IN, 7748))
        game.update_game(2, (PokerAction.ALL_IN, 24786))
        game.end_round()
        
        # Round 1: Both players are all-in from previous round
        game.start_round()
        game.update_game(1, (PokerAction.ALL_IN, 0))  # Already all-in
        game.update_game(2, (PokerAction.ALL_IN, 0))  # Already all-in
        game.end_round()
        
        # Round 2: Both players are all-in from previous round
        game.start_round()
        game.update_game(1, (PokerAction.ALL_IN, 0))  # Already all-in
        game.update_game(2, (PokerAction.ALL_IN, 0))  # Already all-in
        game.end_round()
        
        # Round 3: Both players are all-in from previous round
        game.start_round()
        game.update_game(1, (PokerAction.ALL_IN, 0))  # Already all-in
        game.update_game(2, (PokerAction.ALL_IN, 0))  # Already all-in
        game.end_round()
        
        # End the game to calculate final scores
        game.end_game()
        
        print(f"Final scores: {game.score}")
        print(f"Player 1 total bet: 7748")
        print(f"Player 2 total bet: 24786")
        print(f"Total pot: {sum(game.score.values()) + 7748 + 24786}")
        
        # Player 1 should win, but can only win up to 2 * 7748 = 15496 chips
        # (their all-in amount from each player)
        self.assertLessEqual(game.score[1], 7748)  # Should win at most their all-in amount
        self.assertGreaterEqual(game.score[2], -15496)  # Should lose at most 2 * opponent's all-in amount
        
        # Verify zero-sum
        self.assertEqual(sum(game.score.values()), 0)


if __name__ == '__main__':
    unittest.main() 