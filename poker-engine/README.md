[![Push Docker Image to Docker Hub](https://github.com/ATC-UW/pokerden-engine/actions/workflows/docker_publish.yml/badge.svg)](https://github.com/ATC-UW/pokerden-engine/actions/workflows/docker_publish.yml)

[![Run Tests](https://github.com/ATC-UW/pokerden-engine/actions/workflows/test.yml/badge.svg)](https://github.com/ATC-UW/pokerden-engine/actions/workflows/test.yml)

# PokerDen Engine

PokerDen Engine is a Python-based poker game server designed for poker bot development and testing. It provides a complete Texas Hold'em poker implementation with socket-based communication for real-time multiplayer gameplay.

## Architecture

The engine consists of several key components:

- **Game Logic** (`game/game.py`): Core poker rules, hand dealing, and scoring
- **Server** (`server.py`): Socket server handling client connections and game flow
- **Round State** (`game/round_state.py`): Betting round management and pot calculation
- **Message Protocol** (`message.py`): JSON-based communication between server and clients
- **Configuration** (`config.py`): Centralized settings and file paths

## Installation

### Prerequisites
- Python 3.7+
- pip

### Setup

1. Clone the repository:
    ```bash
    git clone https://github.com/ATC-UW/pokerden-engine.git
    cd pokerden-engine
    ```

2. Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Basic Usage

**Start a single game server:**
```bash
python main.py
```

**Start with custom settings:**
```bash
python main.py --host 0.0.0.0 --port 5000 --players 4 --blind 20
```

### Simulation Mode

**Run continuous simulation:**
```bash
python main.py --sim --sim-rounds 100 --blind 10
```

### Command Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--host` | `0.0.0.0` | Server host address |
| `--port` | `5000` | Server port number |
| `--players` | `2` | Number of required players |
| `--timeout` | `30` | Turn timeout in seconds |
| `--blind` | `10` | Blind amount (small blind = half) |
| `--blind-multiplier` | `1.0` | Factor to multiply blind amount by (default: 1.0 = no increase) |
| `--blind-increase-interval` | `0` | Number of games after which to increase blinds (default: 0 = never increase) |
| `--debug` | `False` | Enable debug logging |
| `--sim` | `False` | Enable simulation mode |
| `--sim-rounds` | `6` | Number of games in simulation |
| `--log-file` | `None` | Log file path |

## Game Flow

1. **Server Startup**: Server starts and waits for players to connect
2. **Player Connection**: Clients connect via TCP sockets
3. **Game Initialization**: Cards dealt, blinds assigned and posted
4. **Betting Rounds**: Players act in sequence through all betting rounds
5. **Showdown**: Best hand wins the pot
6. **Game End**: Results logged, dealer button rotates (in continuous mode)

## Output Files

- **Single Game Mode**: Results written to `output/game_result.log`
- **Simulation Mode**: Results written to `output/sim_result.log`
- **Docker Mode**: Files written to `/app/output/`

## Blind System

- **Small Blind**: Half of the blind amount
- **Big Blind**: Full blind amount
- **Rotation**: Dealer button rotates clockwise after each game
- **Heads-Up**: Dealer posts small blind, opponent posts big blind
- **Multi-Player**: Small blind left of dealer, big blind left of small blind

### Blind Increase System

The engine supports automatic blind increases during continuous games or simulations:

- **Blind Multiplier**: Factor by which blinds are multiplied (e.g., 2.0 doubles blinds)
- **Increase Interval**: Number of games after which blinds increase
- **Formula**: `new_blind = initial_blind × (multiplier ^ increase_count)`

**Examples:**
```bash
# Double blinds every 5 games
python main.py --sim --blind-multiplier 2.0 --blind-increase-interval 5

# Increase blinds by 50% every 10 games
python main.py --sim --blind-multiplier 1.5 --blind-increase-interval 10

# No blind increase (default)
python main.py --sim --blind-multiplier 1.0 --blind-increase-interval 0
```

## Development

### Project Structure
```
pokerden-engine/
├── game/
│   ├── game.py          # Core game logic
│   └── round_state.py   # Betting round management
├── poker_type/          # Type definitions and utilities
├── message.py           # Communication protocol
├── server.py            # Main server implementation
├── main.py              # Entry point
├── config.py            # Configuration settings
└── requirements.txt     # Python dependencies
```

### Testing

Run the test suite:
```bash
python -m pytest tests/
```

Run with debug output:
```bash
python main.py --debug --players 2
```

## Docker Usage

Build and run with Docker:
```bash
docker build -t pokerden-engine .
docker run -p 5000:5000 pokerden-engine --sim --sim-rounds 10
```

## Integration

This engine is designed to work with the [poker-client](https://github.com/ATC-UW/poker-client) for complete bot development and testing workflows. Clients connect via TCP sockets and implement the Bot interface to play poker games.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions, issues, or contributions, please open an issue on GitHub or contact the development team.

## Logging

The server supports comprehensive logging with the following features:

- **Console Logging**: Default behavior, logs to stdout
- **File Logging**: Use `--log-file` to log to a specific file
- **Log Levels**: 
  - INFO: General server activity, game events, player actions
  - DEBUG: Detailed game state, message exchanges (when `--debug` is used)
  - WARNING: Non-critical issues
  - ERROR: Errors and exceptions

### Example Log Files

- `server.log`: General server logs
- `simulation.log`: Simulation mode logs
- `debug.log`: Debug mode logs with detailed information

## Configuration

Server configuration can be modified in `config.py`:

- `NUM_ROUNDS`: Default number of simulation rounds
- `OUTPUT_FILE_SIMULATION`: Simulation output file path
- `OUTPUT_GAME_RESULT_FILE`: Game result output file path
- `SERVER_SIM_WAIT_BETWEEN_GAMES`: Wait time between games in simulation mode