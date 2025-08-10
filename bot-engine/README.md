# 🃏 HuskyHoldem Client

This repository contains the poker library framework for **HuskyHoldem**, a heads-up poker competition platform. Players will implement their own bot logic to compete in matches hosted by a central game server.

## About Huskyholdem

HuskyHoldem is a platform designed to facilitate heads-up poker competitions. It provides a centralized game server where players can test their bot strategies against others in a fair and competitive environment. The platform supports a variety of poker rules and game configurations, making it an excellent tool for learning, experimenting, and showcasing AI-driven poker strategies. 

For more details about the competition, rules, and scoring, visit the [official HuskyHoldem website](https://huskyholdem.atcuw.org/).

## 📁 Project Structure

As player, you should only need to care about these files
```
huskyholdem-client/
├── player.py                  # Where players implement their bot logic (SimplePlayer)
├── type/                   # Type definitions for game state and actions
│   ├── poker_action.py
│   └── round_state.py
├── requirements.txt        # Python dependencies
└── README.md               # You're here!
```
---

## 🚀 Getting Started

1. **Clone the repo**
   ```bash
   git clone https://github.com/your-org/huskyholdem-client.git
   cd huskyholdem-client
   ```

2. **Setup virtual env (Optional)**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run locally (would also need to set up [pokerden-engine](https://github.com/ATC-UW/pokerden-engine) to simulate)**
   ```bash
   python main.py
   ```

---

## 🤖 Implement Your Bot

To participate, you only need to edit the `SimplePlayer` class in `bot.py`. Do **not** change the class name.

Here’s the template you're given:

```python
class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        print("Player called on game start")
        print("Player hands: ", player_hands)
        print("Blind: ", blind_amount)
        print("Big blind player id: ", big_blind_player_id)
        print("Small blind player id: ", small_blind_player_id)
        print("All players in game: ", all_players)

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        print("Player called on round start")
        print("Round state: ", round_state)

    def get_action(self, round_state: RoundStateClient, remaining_chips: int):
        """ Returns the action for the player. """
         ...

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        """ Called at the end of the round. """
        print("Player called on end round")

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        print("Player called on end game, with player score: ", player_score)
        print("All final scores: ", all_scores)
        print("Active players hands: ", active_players_hands)
```

You may modify the logic inside each function as well as extend it (don't remove any predefined function - `on_end_game`, `on_round_start`, `get_action`,`on_end_round`,`on_end_game`), but the class name `SimplePlayer` **must remain unchanged** for compatibility with the game server.

---

## 🛠 Dev Tips

- `RoundStateClient` contains all relevant game state.
- Use `PokerAction.RAISE`, `CALL`, `CHECK`, and `FOLD` to return your move.
- Logs are printed to standard output and result is saved in `game_result.log`.

---

## 🐳 Docker Support

Build and run your bot in a container:

```bash
docker build -t huskyholdem-client .
docker run huskyholdem-client
```

---

## 📬 Contact

Questions? Reach out to the HuskyHoldem team or open an issue.

---

🏆 _Ready to compete? Implement your strategy and join the game!_
