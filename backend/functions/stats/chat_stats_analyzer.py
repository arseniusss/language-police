from typing import List, Dict, Any
from collections import defaultdict
from middlewares.database.models import User

class ChatStatsAnalyzer:
    """Analyzer for chat-wide statistics across all members"""
    
    def __init__(self, users: List[User], chat_id: str):
        self.users = users
        self.chat_id = str(chat_id)
        
    def total_member_count(self) -> int:
        """Get total number of members in chat"""
        return len(self.users)
    
    def members_with_messages_count(self) -> int:
        """Get number of members who have sent messages that were analyzed"""
        count = 0
        for user in self.users:
            if self.chat_id in user.chat_history and user.chat_history[self.chat_id]:
                count += 1
        return count
    
    def total_messages_count(self) -> int:
        """Get total number of analyzed messages in the chat"""
        total = 0
        for user in self.users:
            if self.chat_id in user.chat_history:
                total += len(user.chat_history[self.chat_id])
        return total
    
    def total_message_length(self) -> int:
        """Get total length of all analyzed messages in the chat"""
        total_length = 0
        for user in self.users:
            if self.chat_id in user.chat_history:
                for msg in user.chat_history[self.chat_id]:
                    total_length += len(msg.content)
        return total_length
    
    def language_counts(self) -> Dict[str, int]:
        """Get count of messages by language with prob > 0.5"""
        lang_counts = defaultdict(int)
        
        for user in self.users:
            if self.chat_id in user.chat_history:
                for msg in user.chat_history[self.chat_id]:
                    if msg.analysis_result:
                        top_lang = msg.analysis_result[0]  # First result is highest probability
                        if top_lang["prob"] > 0.5:
                            lang_counts[top_lang["lang"]] += 1
                            
        return lang_counts
    
    def total_unique_languages(self) -> int:
        """Get total number of unique languages detected in the chat"""
        return len(self.language_counts())
        
    def generate_stats_report(self) -> Dict[str, Any]:
        """Generate a comprehensive stats report for the chat"""
        language_counts = self.language_counts()
        total_messages = self.total_messages_count()
        
        # Calculate language percentages
        language_percentages = {}
        for lang, count in language_counts.items():
            if total_messages > 0:
                language_percentages[lang] = (count / total_messages) * 100
            else:
                language_percentages[lang] = 0
        
        return {
            "total_members": self.total_member_count(),
            "members_with_messages": self.members_with_messages_count(),
            "total_messages": total_messages,
            "total_message_length": self.total_message_length(),
            "total_unique_languages": self.total_unique_languages(),
            "language_counts": dict(sorted(language_counts.items(), key=lambda x: x[1], reverse=True)),
            "language_percentages": dict(sorted(language_percentages.items(), key=lambda x: x[1], reverse=True))
        }