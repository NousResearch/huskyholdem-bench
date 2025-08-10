import unittest
import sys
import os

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.game import Game
from poker_type.game import PokerAction
import eval7


class TestSidePotsExtensive(unittest.TestCase):
    
    def test_three_all_ins_different_amounts(self):
        """Test three players with different all-in amounts creating multiple side pots"""
        game = Game(debug=True)
        
        game.add_player(1)
        game.add_player(2)
        game.add_player(3)
        game.add_player(4)
        
        game.start_game()
        
        # Set hands: Player 4 has the best hand despite being the biggest loser
        game.hands[1] = [eval7.Card("2s"), eval7.Card("3d")]  # Weakest
        game.hands[2] = [eval7.Card("4s"), eval7.Card("5d")]  # Second weakest
        game.hands[3] = [eval7.Card("6s"), eval7.Card("7d")]  # Second strongest  
        game.hands[4] = [eval7.Card("As"), eval7.Card("Ad")]  # Strongest (Aces)
        
        # Board with no help
        game.board = [eval7.Card("Th"), eval7.Card("Js"), eval7.Card("Qh"), eval7.Card("Kc"), eval7.Card("9h")]
        
        # Different all-in amounts
        game.update_game(1, (PokerAction.ALL_IN, 25))   # Smallest all-in
        game.update_game(2, (PokerAction.ALL_IN, 75))   # Medium all-in  
        game.update_game(3, (PokerAction.ALL_IN, 150))  # Large all-in
        game.update_game(4, (PokerAction.CALL, 150))    # Calls the largest
        
        # Verify side pot creation
        self.assertEqual(len(game.current_round.pots), 3)
        
        # Main pot: 25 * 4 = 100 (all players eligible)
        pot1 = game.current_round.pots[0]
        self.assertEqual(pot1.amount, 100)
        self.assertEqual(pot1.eligible_players, {1, 2, 3, 4})
        
        # Side pot 1: (75-25) * 3 = 150 (players 2,3,4 eligible)
        pot2 = game.current_round.pots[1]
        self.assertEqual(pot2.amount, 150)
        self.assertEqual(pot2.eligible_players, {2, 3, 4})
        
        # Side pot 2: (150-75) * 2 = 150 (players 3,4 eligible)
        pot3 = game.current_round.pots[2]
        self.assertEqual(pot3.amount, 150)
        self.assertEqual(pot3.eligible_players, {3, 4})
        
        game.end_round()
        game.end_game()
        
        # Player 4 should win all pots with Aces: 100 + 150 + 150 = 400
        # Final scores: P1: -25, P2: -75, P3: -150, P4: +250
        expected_scores = {1: -25, 2: -75, 3: -150, 4: 250}
        
        for player, expected_score in expected_scores.items():
            self.assertEqual(game.score[player], expected_score, 
                           f"Player {player} expected {expected_score}, got {game.score[player]}")
        
        # Verify zero-sum
        self.assertEqual(sum(game.score.values()), 0)
        print(f"✅ Three all-ins test: {game.score}")

    def test_folded_player_not_in_side_pots(self):
        """Test that folded players are not eligible for any pots"""
        game = Game(debug=True)
        
        game.add_player(1)
        game.add_player(2)
        game.add_player(3)
        game.add_player(4)
        
        game.start_game()
        
        # Set hands
        game.hands[1] = [eval7.Card("As"), eval7.Card("Ad")]  # Best hand (but will fold)
        game.hands[2] = [eval7.Card("Ks"), eval7.Card("Kd")]  # Second best
        game.hands[3] = [eval7.Card("Qs"), eval7.Card("Qd")]  # Third best
        game.hands[4] = [eval7.Card("Js"), eval7.Card("Jd")]  # Worst (but will win)
        
        game.board = [eval7.Card("2h"), eval7.Card("3s"), eval7.Card("4d"), eval7.Card("7c"), eval7.Card("9h")]
        
        # Player 1 raises then folds (loses money but not eligible for pots)
        game.update_game(1, (PokerAction.RAISE, 50))
        game.update_game(2, (PokerAction.ALL_IN, 100))  # All-in for 100 total
        game.update_game(3, (PokerAction.ALL_IN, 200))  # All-in for 200 total
        game.update_game(4, (PokerAction.CALL, 200))    # Calls 200
        game.update_game(1, (PokerAction.FOLD, 0))      # Folds after initial raise
        
        # Check that folded player is not in any pots
        for pot in game.current_round.pots:
            self.assertNotIn(1, pot.eligible_players)
        
        game.end_round()
        game.end_game()
        
        # Player 1 should lose their initial bet (50) and win nothing
        self.assertEqual(game.score[1], -50)
        
        # Verify zero-sum
        self.assertEqual(sum(game.score.values()), 0)
        print(f"✅ Folded player test: {game.score}")

    def test_everyone_all_in_same_amount(self):
        """Test when everyone goes all-in for the same amount"""
        game = Game(debug=True)
        
        game.add_player(1)
        game.add_player(2)
        game.add_player(3)
        game.add_player(4)
        
        game.start_game()
        
        # Set hands for clear winner
        game.hands[1] = [eval7.Card("As"), eval7.Card("Ad")]  # Aces (winner)
        game.hands[2] = [eval7.Card("Ks"), eval7.Card("Kd")]  # Kings
        game.hands[3] = [eval7.Card("Qs"), eval7.Card("Qd")]  # Queens
        game.hands[4] = [eval7.Card("Js"), eval7.Card("Jd")]  # Jacks
        
        game.board = [eval7.Card("2h"), eval7.Card("3s"), eval7.Card("4d"), eval7.Card("7c"), eval7.Card("9h")]
        
        # Everyone goes all-in for the same amount
        game.update_game(1, (PokerAction.ALL_IN, 100))
        game.update_game(2, (PokerAction.ALL_IN, 100))
        game.update_game(3, (PokerAction.ALL_IN, 100))
        game.update_game(4, (PokerAction.ALL_IN, 100))
        
        # Should create only one pot since all amounts are equal
        self.assertEqual(len(game.current_round.pots), 1)
        self.assertEqual(game.current_round.pots[0].amount, 400)
        self.assertEqual(game.current_round.pots[0].eligible_players, {1, 2, 3, 4})
        
        game.end_round()
        game.end_game()
        
        # Player 1 should win everything: 400 - 100 = +300
        # Others should lose: 0 - 100 = -100 each
        self.assertEqual(game.score[1], 300)
        self.assertEqual(game.score[2], -100)
        self.assertEqual(game.score[3], -100)
        self.assertEqual(game.score[4], -100)
        
        # Verify zero-sum
        self.assertEqual(sum(game.score.values()), 0)
        print(f"✅ Everyone all-in same amount test: {game.score}")

    def test_ties_in_side_pots(self):
        """Test tied hands in side pot scenarios"""
        game = Game(debug=True)
        
        game.add_player(1)
        game.add_player(2)
        game.add_player(3)
        game.add_player(4)
        
        game.start_game()
        
        # Set hands for ties - Players 1 and 2 tie with Aces, Player 3 has Kings, Player 4 has Queens
        game.hands[1] = [eval7.Card("As"), eval7.Card("Ad")]  # Aces (tie for best)
        game.hands[2] = [eval7.Card("Ac"), eval7.Card("Ah")]  # Aces (tie for best)
        game.hands[3] = [eval7.Card("Ks"), eval7.Card("Kd")]  # Kings
        game.hands[4] = [eval7.Card("Qs"), eval7.Card("Qd")]  # Queens
        
        game.board = [eval7.Card("2h"), eval7.Card("3s"), eval7.Card("4d"), eval7.Card("7c"), eval7.Card("9h")]
        
        # Create side pot scenario
        game.update_game(1, (PokerAction.ALL_IN, 40))   # Smallest all-in
        game.update_game(2, (PokerAction.ALL_IN, 80))   # Medium all-in
        game.update_game(3, (PokerAction.ALL_IN, 120))  # Large all-in
        game.update_game(4, (PokerAction.CALL, 120))    # Calls largest
        
        game.end_round()
        game.end_game()
        
        # Players 1 and 2 should split the main pot (they both have Aces)
        # Player 2 should win additional side pots where Player 1 is not eligible
        
        # Verify zero-sum
        self.assertEqual(sum(game.score.values()), 0)
        print(f"✅ Ties in side pots test: {game.score}")

    def test_zero_pot_edge_case(self):
        """Test edge case where pot could be zero (all players check)"""
        game = Game(debug=True)
        
        game.add_player(1)
        game.add_player(2)
        
        game.start_game()
        
        # Set hands
        game.hands[1] = [eval7.Card("As"), eval7.Card("Ad")]
        game.hands[2] = [eval7.Card("Ks"), eval7.Card("Kd")]
        
        game.board = [eval7.Card("2h"), eval7.Card("3s"), eval7.Card("4d"), eval7.Card("7c"), eval7.Card("9h")]
        
        # Both players check (no bets)
        game.update_game(1, (PokerAction.CHECK, 0))
        game.update_game(2, (PokerAction.CHECK, 0))
        
        game.end_round()
        game.end_game()
        
        # Both players should have score 0 (no money won or lost)
        self.assertEqual(game.score[1], 0)
        self.assertEqual(game.score[2], 0)
        
        # Verify zero-sum
        self.assertEqual(sum(game.score.values()), 0)
        print(f"✅ Zero pot edge case test: {game.score}")

    def test_multiple_rounds_with_escalating_bets(self):
        """Test multiple rounds with increasing bet sizes"""
        game = Game(debug=True)
        
        game.add_player(1)
        game.add_player(2)
        game.add_player(3)
        
        game.start_game()
        
        # Set hands
        game.hands[1] = [eval7.Card("As"), eval7.Card("Ad")]  # Aces (best)
        game.hands[2] = [eval7.Card("Ks"), eval7.Card("Kd")]  # Kings
        game.hands[3] = [eval7.Card("Qs"), eval7.Card("Qd")]  # Queens
        
        game.board = [eval7.Card("2h"), eval7.Card("3s"), eval7.Card("4d"), eval7.Card("7c"), eval7.Card("9h")]
        
        # Round 1: Small bets
        game.update_game(1, (PokerAction.RAISE, 10))
        game.update_game(2, (PokerAction.CALL, 10))
        game.update_game(3, (PokerAction.CALL, 10))
        
        game.end_round()
        game.start_round()  # Move to next round
        
        # Round 2: Medium bets
        game.update_game(1, (PokerAction.RAISE, 50))
        game.update_game(2, (PokerAction.CALL, 50))
        game.update_game(3, (PokerAction.CALL, 50))
        
        game.end_round()
        game.start_round()  # Move to next round
        
        # Round 3: Large bets
        game.update_game(1, (PokerAction.RAISE, 200))
        game.update_game(2, (PokerAction.CALL, 200))
        game.update_game(3, (PokerAction.FOLD, 0))  # Fold on large bet
        
        game.end_round()
        game.end_game()
        
        # Total pot should be: (10+50+200)*2 + 10+50 = 520 + 60 = 580
        # Player 1 should win with Aces
        
        # Verify zero-sum
        print(game.score)
        self.assertEqual(sum(game.score.values()), 0)
        print(f"✅ Multiple rounds escalating test: {game.score}")


if __name__ == '__main__':
    unittest.main() 