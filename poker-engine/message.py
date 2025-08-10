import json
from typing import List
from poker_type.messsage import GameStateMessage, MessageType, RequestPlayerActionMessage
from eval7 import Card

class Message:
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

    def serialize(self):
        return "Not implemented"

    def __repr__(self):
        return self.message
    
class CONNECT(Message):
    def __init__(self, player_id):
        self.message = player_id
        self.type = MessageType.CONNECT

    def serialize(self):
        return json.dumps({"type": self.type.value, "message": self.message})

    def __str__(self):
        return self.serialize()

    @staticmethod
    def parse(message_str):
        data = json.loads(message_str)
        if data["type"] == MessageType.CONNECT.value:
            return CONNECT(data["message"])
        return Message(data["message"])

    
class END(Message):
    def __init__(self, score, all_scores=None, active_players_hands=None):
        self.message = score  # Individual player's score for backwards compatibility
        self.all_scores = all_scores or {}  # Dictionary of all player scores
        self.active_players_hands = active_players_hands or {}  # Dictionary of all player hands
        self.type = MessageType.GAME_END

    def serialize(self):
        return json.dumps({
            "type": self.type.value, 
            "message": {
                "player_score": self.message,
                "all_scores": self.all_scores,
                "active_players_hands": self.active_players_hands
            }
        })

    def __str__(self):
        return self.serialize()

    @staticmethod
    def parse(message_str):
        data = json.loads(message_str)
        if data["type"] == MessageType.GAME_END.value:
            msg_data = data["message"]
            return END(
                msg_data.get("player_score", 0),
                msg_data.get("all_scores", {}),
                msg_data.get("active_players_hands", {})
            )
        return Message(data["message"])
    
class START(Message):
    def __init__(self, message: str, hands: List[str], blind_amount: int = 0, is_small_blind: bool = False, is_big_blind: bool = False, small_blind_player_id: int = None, big_blind_player_id: int = None, all_players: List[int] = None):
        self.message = message
        self.type = MessageType.GAME_START
        self.hands = hands
        self.blind_amount = blind_amount
        self.is_small_blind = is_small_blind
        self.is_big_blind = is_big_blind
        self.small_blind_player_id = small_blind_player_id
        self.big_blind_player_id = big_blind_player_id
        self.all_players = all_players or []

    def serialize(self):
        return json.dumps({"type": self.type.value, "message": {
            "message": self.message,
            "hands": self.hands,
            "blind_amount": self.blind_amount,
            "is_small_blind": self.is_small_blind,
            "is_big_blind": self.is_big_blind,
            "small_blind_player_id": self.small_blind_player_id,
            "big_blind_player_id": self.big_blind_player_id,
            "all_players": self.all_players
        }})

    def __str__(self):
        return self.serialize()

    @staticmethod
    def parse(message_str):
        data = json.loads(message_str)
        if data["type"] == MessageType.GAME_START.value:
            msg_data = data["message"]
            return START(
                msg_data.get("message", ""),
                msg_data.get("hands", []),
                msg_data.get("blind_amount", 0),
                msg_data.get("is_small_blind", False),
                msg_data.get("is_big_blind", False),
                msg_data.get("small_blind_player_id", None),
                msg_data.get("big_blind_player_id", None),
                msg_data.get("all_players", [])
            )
        return Message(data["message"])
    
class ROUND_END(Message):
    def __init__(self, message):
        self.message = message
        self.type = MessageType.ROUND_END

    def serialize(self):
        return json.dumps({"type": self.type.value, "round": self.message})

    def __str__(self, message):
        return self.serialize()

    @staticmethod
    def parse(message_str):
        data = json.loads(message_str)
        if data["type"] == MessageType.ROUND_END.value:
            return ROUND_END(data["message"])
        return Message(data["message"])

class ROUND_START(Message):
    def __init__(self, message):
        self.round = message
        self.type = MessageType.ROUND_START

    def serialize(self):
        return json.dumps({"type": self.type.value, "message": self.round})
    
    def __str__(self):
        return self.serialize()
    
    @staticmethod
    def parse(message_str):
        data = json.loads(message_str)
        if data["type"] == MessageType.ROUND_START.value:
            return ROUND_START(data["message"])
        return Message(data["message"])
    
class ROUND_END(Message):
    def __init__(self, round):
        self.round = round
        self.type = MessageType.ROUND_END

    def serialize(self):
        return json.dumps({"type": self.type.value, "message": self.round})
    
    def __str__(self):
        return self.serialize()
    
    @staticmethod
    def parse(message_str):
        data = json.loads(message_str)
        if data["type"] == MessageType.ROUND_END.value:
            return ROUND_END(data["message"])
        return Message(data["message"])
    
class TEXT(Message):
    def __init__(self, message):
        self.message: str = message
        self.type = MessageType.MESSAGE
    
    def serialize(self):
        return json.dumps({"type": self.type.value, "message": self.message})
    
    def __str__(self):
        return self.serialize()
    
    @staticmethod
    def parse(message_str):
        data = json.loads(message_str)
        if data["type"] == str(MessageType.MESSAGE):
            return TEXT(data["message"])
        raise ValueError("Invalid message type")

class GAME_STATE(Message):
    def __init__(self, game_state: GameStateMessage):
        self.message: GameStateMessage = game_state
        self.type = MessageType.GAME_STATE

    def serialize(self):
        return json.dumps({
            "type": self.type.value,
            "message": {
                "round_num": self.message.round_num,
                "round": self.message.round,
                "community_cards": [str(card) for card in self.message.community_cards],
                "pot": self.message.pot,
                "current_player": list(self.message.current_player),
                "current_bet": self.message.current_bet,
                "player_bets": self.message.player_bets,
                "player_actions": self.message.player_actions,
                "min_raise": self.message.min_raise,
                "max_raise": self.message.max_raise,
                "side_pots": self.message.side_pots or []
            }
        })
    
    def __str__(self):
        return self.serialize()
    
    @staticmethod
    def parse(message_str):
        data = json.loads(message_str)
        if data["type"] == MessageType.GAME_STATE.value:
            msg = data["message"]
            # Convert back into GameStateMessage object
            game_state = GameStateMessage(
                round_num=msg["round_num"],
                round=msg["round"],
                community_cards=[Card(c) for c in msg["community_cards"]],
                pot=msg["pot"],
                current_player=set(msg["current_player"]),
                current_bet=msg["current_bet"],
                player_bets=msg["player_bets"],
                player_actions=msg["player_actions"],
                min_raise=msg["min_raise"],
                max_raise=msg["max_raise"],
                side_pots=msg.get("side_pots", [])
            )
            return GAME_STATE(game_state)
        raise ValueError("Invalid message type")
    
class REQUEST_PLAYER_MESSAGE(Message):
    def __init__(self, player_id, time_left):
        self.message: RequestPlayerActionMessage = RequestPlayerActionMessage(
                player_id=player_id,
                time_left=time_left
            )
        self.type = MessageType.REQUEST_PLAYER_ACTION
    
    def serialize(self):
        return json.dumps({
            "type": self.type.value,
            "message": {
                "player_id": self.message.player_id,
                "time_left": self.message.time_left
            }
        })

    def __str__(self):
        return self.serialize()
    
    @staticmethod
    def parse(message_str):
        data = json.loads(message_str)
        if data["type"] == MessageType.REQUEST_PLAYER_ACTION.value:
            return REQUEST_PLAYER_MESSAGE(data["player_id"], data["time_left"])
        raise ValueError("Invalid message type")
    
class PLAYER_ACTION(Message):
    def __init__(self, player_id, action, amount):
        self.message = {
            "player_id": player_id,
            "action": action,
            "amount": amount
        }
        self.type = MessageType.PLAYER_ACTION
    
    def serialize(self):
        return json.dumps({"type": self.type.value, "message": {
            "player_id": self.message["player_id"],
            "action": self.message["action"],
            "amount": self.message["amount"]
        }})
    
    def __str__(self):
        return self.serialize()
    
    @staticmethod
    def parse(message_str):
        data = json.loads(message_str)
        if data["type"] == MessageType.PLAYER_ACTION.value:
            return PLAYER_ACTION(data["message"]["player_id"], data["message"]["action"], data["message"]["amount"])
        raise ValueError("Invalid message type")