from eval7 import Deck, Card

class PokerDeck():
    """
    A deck of cards for playing poker.
    Wrapper for extensible integration with eval7.
    """

    def __init__(self):
        self.deck = Deck()

    def deal(self, num_cards: int) -> list:
        """
        Deal a number of cards from the deck.
        """
        return self.deck.deal(num_cards)
    
    def shuffle(self):
        """
        Shuffle the deck.
        """
        self.deck.shuffle()

    def remove(self, card: Card):
        """
        Remove a card from the deck.
        """
        self.deck.cards.remove(card)

    def remove_multiple(self, cards: list):
        """
        Remove multiple cards from the deck.
        """
        for card in cards:
            self.deck.cards.remove(card)
    
    def peek(self, n):
        """
        Peek at the deck.
        """
        return self.deck.peek(n)
    
    def sample(self, n):
        """
        Sample n cards from the deck.
        """
        return self.deck.sample(n)
    
    def __str__(self):
        return str(self.deck.__str__())
    
    def __repr__(self):
        return str(self.deck.__repr__())
    
    def __len__(self):
        return len(self.deck.cards)
    
    def __getitem__(self, i):
        return self.deck.cards[i]
    

    

    