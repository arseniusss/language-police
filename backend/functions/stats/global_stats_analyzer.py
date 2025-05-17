from typing import List, Dict, Any, Set
from collections import defaultdict
from middlewares.database.models import User

class GlobalStatsAnalyzer:
    """Analyzer for system-wide statistics across all users and chats"""
    
    def __init__(self, users: List[User]):
        self.users = users
        
    def total_users_count(self) -> int:
        """Get total number of users in the system"""
        return len(self.users)
    
    def users_with_messages_count(self) -> int:
        """Get number of users who have sent messages that were analyzed"""
        count = 0
        for user in self.users:
            if user.chat_history and any(user.chat_history.values()):
                count += 1
        return count
    
    def total_chats_count(self) -> int:
        """Get total number of unique chats in the system"""
        chat_ids = set()
        for user in self.users:
            for chat_id in user.chat_history.keys():
                chat_ids.add(chat_id)
        return len(chat_ids)
    
    def total_messages_count(self) -> int:
        """Get total number of analyzed messages in the system"""
        total = 0
        for user in self.users:
            for messages in user.chat_history.values():
                total += len(messages)
        return total
    
    def total_message_length(self) -> int:
        """Get total length of all analyzed messages in the system"""
        total_length = 0
        for user in self.users:
            for messages in user.chat_history.values():
                for msg in messages:
                    total_length += len(msg.content)
        return total_length
    
    def language_counts(self) -> Dict[str, int]:
        """Get count of messages by language with prob > 0.5"""
        lang_counts = defaultdict(int)
        
        for user in self.users:
            for chat_id, messages in user.chat_history.items():
                for msg in messages:
                    if msg.analysis_result:
                        top_lang = msg.analysis_result[0]  # First result is highest probability
                        if top_lang["prob"] > 0.5:
                            lang_counts[top_lang["lang"]] += 1
                            
        return lang_counts
    
    def total_unique_languages(self) -> int:
        """Get total number of unique languages detected in the system"""
        return len(self.language_counts())
        
    def chat_message_counts(self) -> Dict[str, int]:
        """Get count of messages by chat"""
        chat_counts = defaultdict(int)
        
        for user in self.users:
            for chat_id, messages in user.chat_history.items():
                chat_counts[chat_id] += len(messages)
                
        return chat_counts
    
    def user_message_counts(self) -> Dict[int, int]:
        """Get count of messages by user"""
        user_counts = {}
        
        for user in self.users:
            total_messages = 0
            for messages in user.chat_history.values():
                total_messages += len(messages)
            user_counts[user.user_id] = total_messages
                
        return user_counts
        
    def generate_stats_report(self) -> Dict[str, Any]:
        """Generate a comprehensive stats report for the system"""
        language_counts = self.language_counts()
        total_messages = self.total_messages_count()
        
        # Calculate language percentages
        language_percentages = {}
        for lang, count in language_counts.items():
            if total_messages > 0:
                language_percentages[lang] = (count / total_messages) * 100
            else:
                language_percentages[lang] = 0
        
        # Top chats by message count
        chat_counts = self.chat_message_counts()
        top_chats = dict(sorted(chat_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        
        # Top users by message count
        user_counts = self.user_message_counts()
        top_users = dict(sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        
        return {
            "total_users": self.total_users_count(),
            "users_with_messages": self.users_with_messages_count(),
            "total_chats": self.total_chats_count(),
            "total_messages": total_messages,
            "total_message_length": self.total_message_length(),
            "total_unique_languages": self.total_unique_languages(),
            "language_counts": dict(sorted(language_counts.items(), key=lambda x: x[1], reverse=True)),
            "language_percentages": dict(sorted(language_percentages.items(), key=lambda x: x[1], reverse=True)),
            "top_chats": top_chats,
            "top_users": top_users
        }