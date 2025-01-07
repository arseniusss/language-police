from enum import Enum

class GeneralBackendQueueMessageType(str, Enum):
    TEXT_TO_ANALYZE = "text_to_analyze"
    STATS_COMMAND_TG = "stats_command_tg"

class TelegramQueueMessageType(str, Enum):
    STATS_COMMAND_ANSWER = "stats_command_tg"

class WorkerResQueueMessageType(str, Enum):
    TEXT_ANALYSIS_COMPLETED = "text_analysis_completed"
