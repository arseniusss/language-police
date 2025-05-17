from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime
from middlewares.database.models import User, ChatMessage

class TopGenerator:
    """Base class for generating top statistics"""
    
    def __init__(self, users: List[User]):
        self.users = users
    
    def _get_most_messages(self, limit: int = 10, languages: List[str] = None) -> List[Tuple[int, str, int]]:
        """Get users with the most messages"""
        user_message_counts = []
        
        for user in self.users:
            if hasattr(user, 'total_messages') and not languages:
                # If we've already calculated it and no language filter
                count = user.total_messages
            else:
                # Calculate message count for all relevant messages
                count = self._count_messages_for_user(user, languages)
            
            if count > 0:  # Only add users with messages
                user_message_counts.append((user.user_id, user.name or str(user.user_id), count))
        
        # Sort by count in descending order
        return sorted(user_message_counts, key=lambda x: x[2], reverse=True)[:limit]
    
    def _get_most_message_length(self, limit: int = 10, languages: List[str] = None) -> List[Tuple[int, str, int]]:
        """Get users with the most total message length"""
        user_length_counts = []
        
        for user in self.users:
            total_length = self._total_message_length_for_user(user, languages)
            if total_length > 0:  # Only include users with actual content
                user_length_counts.append((user.user_id, user.name or str(user.user_id), total_length))
        
        # Sort by length in descending order
        return sorted(user_length_counts, key=lambda x: x[2], reverse=True)[:limit]
    
    def _get_most_ukrainian_messages(self, limit: int = 10) -> List[Tuple[int, str, int]]:
        """Get users with the most Ukrainian messages (confidence > 0.5)"""
        user_ua_counts = []
        
        for user in self.users:
            ua_count = self._count_ukrainian_messages_for_user(user)
            if ua_count > 0:  # Only include users with Ukrainian messages
                user_ua_counts.append((user.user_id, user.name or str(user.user_id), ua_count))
        
        # Sort by count in descending order
        return sorted(user_ua_counts, key=lambda x: x[2], reverse=True)[:limit]
    
    def _get_most_messages_by_language(self, language: str, limit: int = 10) -> List[Tuple[int, str, int]]:
        """Get users with the most messages in a specific language"""
        user_lang_counts = []
        
        for user in self.users:
            lang_count = self._count_language_messages_for_user(user, language)
            if lang_count > 0:  # Only include users with messages in this language
                user_lang_counts.append((user.user_id, user.name or str(user.user_id), lang_count))
        
        # Sort by count in descending order
        return sorted(user_lang_counts, key=lambda x: x[2], reverse=True)[:limit]
    
    def _get_earliest_message_users(self, limit: int = 10, languages: List[str] = None) -> List[Tuple[int, str, str]]:
        """Get users with the earliest recorded messages"""
        user_earliest = []
        
        for user in self.users:
            earliest_timestamp = self._get_earliest_message_timestamp(user, languages)
            if earliest_timestamp:  # Only include users with timestamps
                user_earliest.append((user.user_id, user.name or str(user.user_id), earliest_timestamp))
        
        # Sort by timestamp in ascending order
        return sorted(user_earliest, key=lambda x: x[2])[:limit]
    
    def _get_latest_message_users(self, limit: int = 10, languages: List[str] = None) -> List[Tuple[int, str, str]]:
        """Get users with the latest recorded messages"""
        user_latest = []
        
        for user in self.users:
            latest_timestamp = self._get_latest_message_timestamp(user, languages)
            if latest_timestamp:  # Only include users with timestamps
                user_latest.append((user.user_id, user.name or str(user.user_id), latest_timestamp))
        
        # Sort by timestamp in descending order
        return sorted(user_latest, key=lambda x: x[2], reverse=True)[:limit]
    
    def _get_avg_message_length(self, limit: int = 10, languages: List[str] = None) -> List[Tuple[int, str, float]]:
        """Get users with the highest average message length"""
        user_avg_lengths = []
        
        for user in self.users:
            avg_length = self._compute_avg_message_length(user, languages)
            if avg_length > 0:  # Only include users with valid data
                user_avg_lengths.append((user.user_id, user.name or str(user.user_id), avg_length))
        
        # Sort by avg length in descending order
        return sorted(user_avg_lengths, key=lambda x: x[2], reverse=True)[:limit]
    
    def _count_messages_for_user(self, user: User, languages: List[str] = None) -> int:
        """Count all messages for a user"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _total_message_length_for_user(self, user: User, languages: List[str] = None) -> int:
        """Calculate total message length for a user"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _count_ukrainian_messages_for_user(self, user: User) -> int:
        """Count Ukrainian messages for a user"""
        return self._count_language_messages_for_user(user, "uk")
        
    def _count_language_messages_for_user(self, user: User, language: str) -> int:
        """Count messages for a user in a specific language with >0.5 probability"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _get_earliest_message_timestamp(self, user: User, languages: List[str] = None) -> Optional[str]:
        """Get earliest message timestamp for a user"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _get_latest_message_timestamp(self, user: User, languages: List[str] = None) -> Optional[str]:
        """Get latest message timestamp for a user"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _compute_avg_message_length(self, user: User, languages: List[str] = None) -> float:
        """Compute average message length for a user"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _is_message_in_languages(self, msg: ChatMessage, languages: List[str]) -> bool:
        """Check if a message is in one of the specified languages with probability > 0.5"""
        if not msg.analysis_result:
            return False
            
        for lang_with_prob in msg.analysis_result:
            if lang_with_prob["lang"] in languages and lang_with_prob["prob"] > 0.5:
                return True
                
        return False
    
    def _get_language_counts_for_user(self, user: User) -> Dict[str, int]:
        """Get language usage counts for a user"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _get_top_languages(self, limit: int = 10) -> List[Tuple[str, int, str]]:
        """Get the most used languages in the dataset"""
        lang_counts = defaultdict(int)
        
        for user in self.users:
            user_lang_counts = self._get_language_counts_for_user(user)
            for lang, count in user_lang_counts.items():
                lang_counts[lang] += count
                
        # Get language display names from helper function
        from backend.functions.helpers.get_lang_display import get_language_display
        
        # Sort by count in descending order, filter out zero counts, and include display name
        return [(lang, count, get_language_display(lang)) 
                for lang, count in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)
                if count > 0][:limit]
    
    def generate_top_report(self, limit: int = 10, language: str = None) -> Dict[str, Any]:
        """Generate a comprehensive top report"""
        languages = [language] if language else None
        
        report = {
            "most_messages": self._get_most_messages(limit, languages),
            "most_message_length": self._get_most_message_length(limit, languages),
            "earliest_message_users": self._get_earliest_message_users(limit, languages),
            "latest_message_users": self._get_latest_message_users(limit, languages),
            "highest_avg_message_length": self._get_avg_message_length(limit, languages)
        }
        
        if not language:
            report["most_ukrainian_messages"] = self._get_most_ukrainian_messages(limit)
            report["top_languages"] = self._get_top_languages(limit)
        else:
            report["language_filter"] = language
            report["top_by_language"] = self._get_most_messages_by_language(language, limit)
            
        return report


class ChatTopGenerator(TopGenerator):
    """Generate top statistics for a specific chat"""
    
    def __init__(self, users: List[User], chat_id: str):
        super().__init__(users)
        self.chat_id = str(chat_id)
    
    def _count_messages_for_user(self, user: User, languages: List[str] = None) -> int:
        if self.chat_id not in user.chat_history:
            return 0
            
        if not languages:
            return len(user.chat_history[self.chat_id])
            
        count = 0
        for msg in user.chat_history[self.chat_id]:
            if self._is_message_in_languages(msg, languages):
                count += 1
                
        return count
    
    def _total_message_length_for_user(self, user: User, languages: List[str] = None) -> int:
        if self.chat_id not in user.chat_history:
            return 0
        
        total = 0
        for msg in user.chat_history[self.chat_id]:
            if not languages or self._is_message_in_languages(msg, languages):
                total += len(msg.content)
                
        return total
    
    def _count_ukrainian_messages_for_user(self, user: User) -> int:
        return self._count_language_messages_for_user(user, "uk")
    
    def _count_language_messages_for_user(self, user: User, language: str) -> int:
        if self.chat_id not in user.chat_history:
            return 0
        
        lang_count = 0
        for msg in user.chat_history[self.chat_id]:
            if msg.analysis_result:
                for lang_with_prob in msg.analysis_result:
                    if lang_with_prob["lang"] == language and lang_with_prob["prob"] > 0.5:
                        lang_count += 1
                        break
                        
        return lang_count
    
    def _get_language_counts_for_user(self, user: User) -> Dict[str, int]:
        if self.chat_id not in user.chat_history:
            return {}
            
        lang_counts = defaultdict(int)
        for msg in user.chat_history[self.chat_id]:
            if msg.analysis_result:
                lang_with_prob = msg.analysis_result[0]  # Get top language
                if lang_with_prob["prob"] > 0.5:
                    lang_counts[lang_with_prob["lang"]] += 1
                    
        return lang_counts
    
    def _get_earliest_message_timestamp(self, user: User, languages: List[str] = None) -> Optional[str]:
        if self.chat_id not in user.chat_history or not user.chat_history[self.chat_id]:
            return None
        
        timestamps = []
        for msg in user.chat_history[self.chat_id]:
            if not languages or self._is_message_in_languages(msg, languages):
                timestamps.append(msg.timestamp)
                
        return min(timestamps) if timestamps else None
    
    def _get_latest_message_timestamp(self, user: User, languages: List[str] = None) -> Optional[str]:
        if self.chat_id not in user.chat_history or not user.chat_history[self.chat_id]:
            return None
        
        timestamps = []
        for msg in user.chat_history[self.chat_id]:
            if not languages or self._is_message_in_languages(msg, languages):
                timestamps.append(msg.timestamp)
                
        return max(timestamps) if timestamps else None
    
    def _compute_avg_message_length(self, user: User, languages: List[str] = None) -> float:
        if self.chat_id not in user.chat_history or not user.chat_history[self.chat_id]:
            return 0.0
        
        total_length = 0
        message_count = 0
        
        for msg in user.chat_history[self.chat_id]:
            if not languages or self._is_message_in_languages(msg, languages):
                total_length += len(msg.content)
                message_count += 1
        
        return total_length / message_count if message_count > 0 else 0.0


class GlobalTopGenerator(TopGenerator):
    """Generate global top statistics across all chats"""
    
    def _count_messages_for_user(self, user: User, languages: List[str] = None) -> int:
        total = 0
        for chat_id, messages in user.chat_history.items():
            for msg in messages:
                if not languages or self._is_message_in_languages(msg, languages):
                    total += 1
                    
        return total
    
    def _total_message_length_for_user(self, user: User, languages: List[str] = None) -> int:
        total = 0
        for chat_id, messages in user.chat_history.items():
            for msg in messages:
                if not languages or self._is_message_in_languages(msg, languages):
                    total += len(msg.content)
                    
        return total
    
    def _count_ukrainian_messages_for_user(self, user: User) -> int:
        return self._count_language_messages_for_user(user, "uk")
    
    def _count_language_messages_for_user(self, user: User, language: str) -> int:
        lang_count = 0
        for chat_id, messages in user.chat_history.items():
            for msg in messages:
                if msg.analysis_result:
                    for lang_with_prob in msg.analysis_result:
                        if lang_with_prob["lang"] == language and lang_with_prob["prob"] > 0.5:
                            lang_count += 1
                            break
                            
        return lang_count
    
    def _get_language_counts_for_user(self, user: User) -> Dict[str, int]:
        lang_counts = defaultdict(int)
        for chat_id, messages in user.chat_history.items():
            for msg in messages:
                if msg.analysis_result:
                    lang_with_prob = msg.analysis_result[0]  # Get top language
                    if lang_with_prob["prob"] > 0.5:
                        lang_counts[lang_with_prob["lang"]] += 1
                        
        return lang_counts
    
    def _get_earliest_message_timestamp(self, user: User, languages: List[str] = None) -> Optional[str]:
        all_timestamps = []
        
        for chat_id, messages in user.chat_history.items():
            for msg in messages:
                if not languages or self._is_message_in_languages(msg, languages):
                    all_timestamps.append(msg.timestamp)
        
        return min(all_timestamps) if all_timestamps else None
    
    def _get_latest_message_timestamp(self, user: User, languages: List[str] = None) -> Optional[str]:
        all_timestamps = []
        
        for chat_id, messages in user.chat_history.items():
            for msg in messages:
                if not languages or self._is_message_in_languages(msg, languages):
                    all_timestamps.append(msg.timestamp)
        
        return max(all_timestamps) if all_timestamps else None
    
    def _compute_avg_message_length(self, user: User, languages: List[str] = None) -> float:
        total_length = 0
        message_count = 0
        
        for chat_id, messages in user.chat_history.items():
            for msg in messages:
                if not languages or self._is_message_in_languages(msg, languages):
                    total_length += len(msg.content)
                    message_count += 1
        
        return total_length / message_count if message_count > 0 else 0.0