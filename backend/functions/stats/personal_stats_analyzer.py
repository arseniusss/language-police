from typing import List, Dict, Any
from collections import defaultdict
from middlewares.database.models import ChatMessage

# my_chat_stats
# my_global_stats
class PersonalStatsAnalyzer:
    def __init__(self, chat_history: Dict[str, List[ChatMessage]]):
        self.chat_history = chat_history

    def total_chats_count(self) -> int:
        return len(self.chat_history)
    
    def total_message_count(self) -> int:
        total = 0
        for messages in self.chat_history.values():
            total += len(messages)
        return total

    def total_message_length(self) -> int:
        total_length = 0
        for messages in self.chat_history.values():
            for msg in messages:
                total_length += len(msg.content)
        return total_length
    
    def average_message_length(self) -> float:
        total_length = 0
        total_messages = 0
        for messages in self.chat_history.values():
            for msg in messages:
                total_length += len(msg.content)
                total_messages += 1
        return total_length / total_messages if total_messages else 0.0

    def message_count_by_language(self) -> Dict[str, int]:
        lang_count = defaultdict(int)

        for chat_id, messages in self.chat_history.items():
            for msg in messages:
                if msg.analysis_result:
                    lang_with_prob = msg.analysis_result[0]
                    lang_count[lang_with_prob["lang"]] += 1
        
        return lang_count

    def message_count_by_chat(self) -> Dict[str, int]:
        return {chat_id: len(messages) for chat_id, messages in self.chat_history.items()}

    def avg_message_length_by_chat(self) -> Dict[str, float]:
        avg_lengths = {}
        for chat_id, messages in self.chat_history.items():
            total_length = sum(len(msg.content) for msg in messages)
            avg_lengths[chat_id] = total_length / len(messages) if messages else 0.0
        return avg_lengths

    def _generate_stats_report_general(self) -> Dict[str, Any]:
        return {
            "total_chats": self.total_chats_count(),
            "total_messages": self.total_message_count(),
            "total_message_length": self.total_message_length(),
            "avg_length": self.average_message_length(),
            "message_count_by_chat": self.message_count_by_chat(),
            "avg_length_by_chat": self.avg_message_length_by_chat(),
            "message_count_by_language": self.message_count_by_language()
        }

    def _generate_stats_report_chat(self) -> Dict[str, Any]:
        return {
            "total_messages": self.total_message_count(),
            "total_message_length": self.total_message_length(),
            "avg_length": self.average_message_length(),
            "message_count_by_language": self.message_count_by_language(),
        }

    def generate_stats_report(self, chat_id: int | None = None) -> Dict[str, Any]:
        if chat_id is not None:
            if str(chat_id) in self.chat_history.keys():
                new_history = {int(chat_id): self.chat_history[str(chat_id)]}
                self.chat_history = new_history
            else:
                self.chat_history = {}
        
        return self._generate_stats_report_general() if chat_id is None else self._generate_stats_report_chat()