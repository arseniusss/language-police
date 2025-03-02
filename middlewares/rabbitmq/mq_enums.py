from enum import Enum

class GeneralBackendQueueMessageType(str, Enum):
    TEXT_TO_ANALYZE = "text_to_analyze"
    STATS_COMMAND_TG = "stats_command_tg"
    MY_CHAT_STATS_COMMAND_TG = "my_chat_stats_command_tg"
    MY_GLOBAL_STATS_COMMAND_TG = "my_global_stats_command_tg"
    CHAT_TOP_COMMAND_TG = "chat_top_command_tg"
    GLOBAL_TOP_COMMAND_TG = "global_top_command_tg"
    MY_CHAT_RANKING_COMMAND_TG = "my_chat_ranking_command_tg"
    MY_GLOBAL_RANKING_COMMAND_TG = "my_global_ranking_command_tg"

class TelegramQueueMessageType(str, Enum):
    STATS_COMMAND_ANSWER = "stats_command_tg"
    MY_CHAT_STATS_COMMAND_ANSWER = "my_chat_stats_command_tg"
    MY_GLOBAL_STATS_COMMAND_ANSWER = "my_global_stats_command_tg"
    CHAT_TOP_COMMAND_ANSWER = "chat_top_command_tg"
    GLOBAL_TOP_COMMAND_ANSWER = "global_top_command_tg"
    MY_CHAT_RANKING_COMMAND_ANSWER = "my_chat_ranking_command_tg"
    MY_GLOBAL_RANKING_COMMAND_ANSWER = "my_global_ranking_command_tg"

class WorkerResQueueMessageType(str, Enum):
    TEXT_ANALYSIS_COMPLETED = "text_analysis_completed"