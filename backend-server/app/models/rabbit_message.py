from enum import Enum as PyEnum

class SimulationMessageType(str, PyEnum):
    """
    Enum for simulation message types.
    """
    RUN = "RUN"
    RUN_USER = "RUN_USER"
    SCALE_DOCKER = "SCALE_DOCKER"