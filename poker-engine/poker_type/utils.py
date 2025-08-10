from poker_type.game import PokerAction, PokerRound

ROUND_NAMES_MAPPING_FROM_INDEX = {
    0: "Preflop",
    1: "Flop",
    2: "Turn",
    3: "River"
}

ROUND_NAMES_MAPING = {
    PokerRound.PREFLOP: "Preflop",
    PokerRound.FLOP: "Flop",
    PokerRound.TURN: "Turn",
    PokerRound.RIVER: "River"
}

MESSAGE_TYPE_MAPPING = {
    0: "Connect",
    1: "Disconnect",
    2: "Game Start",
    3: "Round Start",
    4: "Request Player Action",
    5: "Player Action",
    6: "Round End",
    7: "Game End",
    8: "Time Stamp",
    9: "Game State",
    10: "Message"
}

POKER_ACTIONS_MAPPING_FROM_INDEX = {
    1: "Fold",
    2: "Check",
    3: "Call",
    4: "Raise",
    5: "All In"
}

POKER_ACTIONS_MAPPING = {
    PokerAction.FOLD: "Fold",
    PokerAction.CHECK: "Check",
    PokerAction.CALL: "Call",
    PokerAction.RAISE: "Raise",
    PokerAction.ALL_IN: "All In"
}

def get_poker_action_name(action: int) -> str:
    if action not in POKER_ACTIONS_MAPPING_FROM_INDEX:
        raise ValueError(f"Invalid action index: {action}")
    
    return POKER_ACTIONS_MAPPING_FROM_INDEX[action]

def get_poker_action_name_from_enum(action: PokerAction) -> str:
    if action not in POKER_ACTIONS_MAPPING:
        raise ValueError(f"Invalid action 8888: {action}")
    
    return POKER_ACTIONS_MAPPING[action]

def get_poker_action_enum_from_index(action: int) -> PokerAction:
    if action not in POKER_ACTIONS_MAPPING_FROM_INDEX:
        raise ValueError(f"Invalid action index: {action}")
    
    for poker_action, name in POKER_ACTIONS_MAPPING.items():
        if name.lower() == POKER_ACTIONS_MAPPING_FROM_INDEX[action].lower():
            return poker_action
    raise ValueError(f"Invalid action index: {action}")

def get_poker_action_enum(action_name: str) -> PokerAction:
    for action, name in POKER_ACTIONS_MAPPING.items():
        if name.lower() == action_name.lower():
            return action
    raise ValueError(f"Invalid action name: {action_name}")

def get_message_type_name(message_type: int) -> str:
    if message_type not in MESSAGE_TYPE_MAPPING:
        raise ValueError(f"Invalid message type: {message_type}")
    return MESSAGE_TYPE_MAPPING[message_type]

def get_round_name(round_index: int) -> str:

    if round_index not in ROUND_NAMES_MAPPING_FROM_INDEX:
        raise ValueError(f"Invalid round index: {round_index}")

    return ROUND_NAMES_MAPPING_FROM_INDEX[round_index]

def get_round_name_from_enum(round: PokerRound) -> str:
    if round not in ROUND_NAMES_MAPING:
        raise ValueError(f"Invalid round enum: {round}")
    return ROUND_NAMES_MAPING[round]