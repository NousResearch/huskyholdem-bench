"""
Warning: this file needs to always be in sync with the game engine server.
The game engine server uses this file to determine the message types and their corresponding names.
"""

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

def get_message_type_name(message_type: int) -> str:
    if message_type not in MESSAGE_TYPE_MAPPING:
        raise ValueError(f"Invalid message type: {message_type}")
    return MESSAGE_TYPE_MAPPING[message_type]