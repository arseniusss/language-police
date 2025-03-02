from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime
from middlewares.database.models import User, ChatMessage

class TopGenerator:
    """Base class for generating top statistics"""
    
    def __init__(self, users: List[User]):
        self.users = users
    
    def _get_most_messages(self, limit: int = 10) -> List[Tuple[int, str, int]]:
        """Get users with the most messages"""
        user_message_counts = []
        
        for user in self.users:
            if hasattr(user, 'total_messages'):
                # If we've already calculated it
                count = user.total_messages
            else:
                # Calculate message count for all relevant messages
                count = self._count_messages_for_user(user)
            
            user_message_counts.append((user.user_id, user.name or str(user.user_id), count))
        
        # Sort by count in descending order
        return sorted(user_message_counts, key=lambda x: x[2], reverse=True)[:limit]
    
    def _get_most_message_length(self, limit: int = 10) -> List[Tuple[int, str, int]]:
        """Get users with the most total message length"""
        user_length_counts = []
        
        for user in self.users:
            total_length = self._total_message_length_for_user(user)
            user_length_counts.append((user.user_id, user.name or str(user.user_id), total_length))
        
        # Sort by length in descending order
        return sorted(user_length_counts, key=lambda x: x[2], reverse=True)[:limit]
    
    def _get_most_ukrainian_messages(self, limit: int = 10) -> List[Tuple[int, str, int]]:
        """Get users with the most Ukrainian messages (confidence > 0)"""
        user_ua_counts = []
        
        for user in self.users:
            ua_count = self._count_ukrainian_messages_for_user(user)
            user_ua_counts.append((user.user_id, user.name or str(user.user_id), ua_count))
        
        # Sort by count in descending order
        return sorted(user_ua_counts, key=lambda x: x[2], reverse=True)[:limit]
    
    def _get_earliest_message_users(self, limit: int = 10) -> List[Tuple[int, str, str]]:
        """Get users with the earliest recorded messages"""
        user_earliest = []
        
        for user in self.users:
            earliest_timestamp = self._get_earliest_message_timestamp(user)
            if earliest_timestamp:
                user_earliest.append((user.user_id, user.name or str(user.user_id), earliest_timestamp))
        
        # Sort by timestamp in ascending order
        return sorted(user_earliest, key=lambda x: x[2])[:limit]
    
    def _get_latest_message_users(self, limit: int = 10) -> List[Tuple[int, str, str]]:
        """Get users with the latest recorded messages"""
        user_latest = []
        
        for user in self.users:
            latest_timestamp = self._get_latest_message_timestamp(user)
            if latest_timestamp:
                user_latest.append((user.user_id, user.name or str(user.user_id), latest_timestamp))
        
        # Sort by timestamp in descending order
        return sorted(user_latest, key=lambda x: x[2], reverse=True)[:limit]
    
    def _get_avg_message_length(self, limit: int = 10) -> List[Tuple[int, str, float]]:
        """Get users with the highest average message length"""
        user_avg_lengths = []
        
        for user in self.users:
            avg_length = self._compute_avg_message_length(user)
            user_avg_lengths.append((user.user_id, user.name or str(user.user_id), avg_length))
        
        # Sort by avg length in descending order
        return sorted(user_avg_lengths, key=lambda x: x[2], reverse=True)[:limit]
    
    def _count_messages_for_user(self, user: User) -> int:
        """Count all messages for a user"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _total_message_length_for_user(self, user: User) -> int:
        """Calculate total message length for a user"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _count_ukrainian_messages_for_user(self, user: User) -> int:
        """Count Ukrainian messages for a user"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _get_earliest_message_timestamp(self, user: User) -> Optional[str]:
        """Get earliest message timestamp for a user"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _get_latest_message_timestamp(self, user: User) -> Optional[str]:
        """Get latest message timestamp for a user"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _compute_avg_message_length(self, user: User) -> float:
        """Compute average message length for a user"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def generate_top_report(self, limit: int = 10) -> Dict[str, Any]:
        """Generate a comprehensive top report"""
        return {
            "most_messages": self._get_most_messages(limit),
            "most_message_length": self._get_most_message_length(limit),
            "most_ukrainian_messages": self._get_most_ukrainian_messages(limit),
            "earliest_message_users": self._get_earliest_message_users(limit),
            "latest_message_users": self._get_latest_message_users(limit),
            "highest_avg_message_length": self._get_avg_message_length(limit)
        }


class ChatTopGenerator(TopGenerator):
    """Generate top statistics for a specific chat"""
    
    def __init__(self, users: List[User], chat_id: str):
        super().__init__(users)
        self.chat_id = str(chat_id)
    
    def _count_messages_for_user(self, user: User) -> int:
        if self.chat_id not in user.chat_history:
            return 0
        return len(user.chat_history[self.chat_id])
    
    def _total_message_length_for_user(self, user: User) -> int:
        if self.chat_id not in user.chat_history:
            return 0
        
        total = 0
        for msg in user.chat_history[self.chat_id]:
            total += len(msg.content)
        return total
    
    def _count_ukrainian_messages_for_user(self, user: User) -> int:
        if self.chat_id not in user.chat_history:
            return 0
        
        ua_count = 0
        for msg in user.chat_history[self.chat_id]:
            if msg.analysis_result:
                for lang_with_prob in msg.analysis_result:
                    if lang_with_prob["lang"] == "uk" and lang_with_prob["prob"] > 0:
                        ua_count += 1
                        break
        return ua_count
    
    def _get_earliest_message_timestamp(self, user: User) -> Optional[str]:
        if self.chat_id not in user.chat_history or not user.chat_history[self.chat_id]:
            return None
        
        timestamps = [msg.timestamp for msg in user.chat_history[self.chat_id]]
        return min(timestamps) if timestamps else None
    
    def _get_latest_message_timestamp(self, user: User) -> Optional[str]:
        if self.chat_id not in user.chat_history or not user.chat_history[self.chat_id]:
            return None
        
        timestamps = [msg.timestamp for msg in user.chat_history[self.chat_id]]
        return max(timestamps) if timestamps else None
    
    def _compute_avg_message_length(self, user: User) -> float:
        if self.chat_id not in user.chat_history or not user.chat_history[self.chat_id]:
            return 0.0
        
        total_length = 0
        message_count = len(user.chat_history[self.chat_id])
        
        for msg in user.chat_history[self.chat_id]:
            total_length += len(msg.content)
        
        return total_length / message_count if message_count > 0 else 0.0


class GlobalTopGenerator(TopGenerator):
    """Generate global top statistics across all chats"""
    
    def _count_messages_for_user(self, user: User) -> int:
        total = 0
        for chat_id, messages in user.chat_history.items():
            total += len(messages)
        return total
    
    def _total_message_length_for_user(self, user: User) -> int:
        total = 0
        for chat_id, messages in user.chat_history.items():
            for msg in messages:
                total += len(msg.content)
        return total
    
    def _count_ukrainian_messages_for_user(self, user: User) -> int:
        ua_count = 0
        for chat_id, messages in user.chat_history.items():
            for msg in messages:
                if msg.analysis_result:
                    for lang_with_prob in msg.analysis_result:
                        if lang_with_prob["lang"] == "uk" and lang_with_prob["prob"] > 0:
                            ua_count += 1
                            break
        return ua_count
    
    def _get_earliest_message_timestamp(self, user: User) -> Optional[str]:
        all_timestamps = []
        
        for chat_id, messages in user.chat_history.items():
            for msg in messages:
                all_timestamps.append(msg.timestamp)
        
        return min(all_timestamps) if all_timestamps else None
    
    def _get_latest_message_timestamp(self, user: User) -> Optional[str]:
        all_timestamps = []
        
        for chat_id, messages in user.chat_history.items():
            for msg in messages:
                all_timestamps.append(msg.timestamp)
        
        return max(all_timestamps) if all_timestamps else None
    
    def _compute_avg_message_length(self, user: User) -> float:
        total_length = 0
        message_count = 0
        
        for chat_id, messages in user.chat_history.items():
            for msg in messages:
                total_length += len(msg.content)
                message_count += 1
        
        return total_length / message_count if message_count > 0 else 0.0