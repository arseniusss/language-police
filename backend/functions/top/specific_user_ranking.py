from typing import List, Dict, Any, Optional, Tuple
from middlewares.database.models import User, ChatMessage
from backend.functions.top.top_generator import TopGenerator, ChatTopGenerator, GlobalTopGenerator

class SpecificUserRankingGenerator:
    """Base class for finding a specific user's ranking in statistics"""
    
    def __init__(self, users: List[User], target_user_id: int):
        self.users = users
        self.target_user_id = target_user_id
        
        self.target_user = None
        for user in self.users:
            if user.user_id == target_user_id:
                self.target_user = user
                break
    
    def _generate_full_rankings(self):
        """Generate all rankings for all categories without limiting to top N"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _find_user_ranking(self, ranking_list, user_id):
        """Find the ranking of the user in a ranking list"""
        for i, (uid, _, _) in enumerate(ranking_list):
            if uid == user_id:
                return i + 1, ranking_list[i]  # 1-based position
        return None, None
    
    def get_user_rankings(self) -> Dict[str, Tuple[int, Any]]:
        """Get the user's ranking in all categories
        
        Returns:
            Dict mapping category names to tuples of (position, value)
        """
        if not self.target_user:
            return {
                "most_messages": (0, 0),
                "most_message_length": (0, 0),
                "most_ukrainian_messages": (0, 0),
                "earliest_message": (0, ""),
                "latest_message": (0, ""),
                "avg_message_length": (0, 0.0)
            }
        
        rankings = self._generate_full_rankings()
        
        positions = {}
        
        # Find position in each category
        for category, ranking_list in rankings.items():
            position, data = self._find_user_ranking(ranking_list, self.target_user_id)
            if position and data:
                positions[category] = (position, data[2])  # position and value
            else:
                # Default values if user not found in ranking
                if category in ["earliest_message", "latest_message"]:
                    positions[category] = (0, "")
                elif category == "avg_message_length":
                    positions[category] = (0, 0.0)
                else:
                    positions[category] = (0, 0)
        
        return positions


class SpecificUserChatRankingGenerator(SpecificUserRankingGenerator):
    """Find a specific user's ranking in chat-based statistics"""
    
    def __init__(self, users: List[User], chat_id: str, target_user_id: int):
        super().__init__(users, target_user_id)
        self.chat_id = chat_id
        self.top_generator = ChatTopGenerator(users, chat_id)
    
    def _generate_full_rankings(self):
        """Generate full rankings for the chat (no limit)"""
        return {
            "most_messages": self.top_generator._get_most_messages(limit=len(self.users)),
            "most_message_length": self.top_generator._get_most_message_length(limit=len(self.users)),
            "most_ukrainian_messages": self.top_generator._get_most_ukrainian_messages(limit=len(self.users)),
            "earliest_message": self.top_generator._get_earliest_message_users(limit=len(self.users)),
            "latest_message": self.top_generator._get_latest_message_users(limit=len(self.users)),
            "avg_message_length": self.top_generator._get_avg_message_length(limit=len(self.users))
        }


class SpecificUserGlobalRankingGenerator(SpecificUserRankingGenerator):
    """Find a specific user's ranking in global statistics"""
    
    def __init__(self, users: List[User], target_user_id: int):
        super().__init__(users, target_user_id)
        self.top_generator = GlobalTopGenerator(users)
    
    def _generate_full_rankings(self):
        """Generate full rankings globally (no limit)"""
        return {
            "most_messages": self.top_generator._get_most_messages(limit=len(self.users)),
            "most_message_length": self.top_generator._get_most_message_length(limit=len(self.users)),
            "most_ukrainian_messages": self.top_generator._get_most_ukrainian_messages(limit=len(self.users)),
            "earliest_message": self.top_generator._get_earliest_message_users(limit=len(self.users)),
            "latest_message": self.top_generator._get_latest_message_users(limit=len(self.users)),
            "avg_message_length": self.top_generator._get_avg_message_length(limit=len(self.users))
        }