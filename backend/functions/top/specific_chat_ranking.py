from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from middlewares.database.models import User, ChatMessage
from backend.functions.top.chat_global_top_generator import ChatGlobalTopGenerator

class SpecificChatRankingGenerator:
    """Find a specific chat's ranking in global chat statistics"""
    
    def __init__(self, users: List[User], target_chat_id: str):
        self.users = users
        self.target_chat_id = str(target_chat_id)
        self.global_top_generator = ChatGlobalTopGenerator(users)
        self.chat_data = self.global_top_generator._aggregate_chat_data()
        
    def get_chat_rankings(self, language: str = None) -> Dict[str, Tuple[int, Any]]:
        """Get the chat's position in various rankings
        
        Returns a dictionary with keys being the ranking type and values being tuples of
        (position, value) where position is the 1-based position of the chat in the ranking
        """
        # Generate full ranking data (no limit)
        full_rankings = self._generate_full_rankings(language)
        
        # Find target chat's position in each ranking
        result = {}
        
        # Most messages
        result["most_messages"] = self._find_position_in_ranking(
            full_rankings["most_messages"], 
            lambda x: x[0] == self.target_chat_id
        )
        
        # Most message length
        result["most_message_length"] = self._find_position_in_ranking(
            full_rankings["most_message_length"], 
            lambda x: x[0] == self.target_chat_id
        )
        
        # Most unique users
        result["most_unique_users"] = self._find_position_in_ranking(
            full_rankings["most_unique_users"], 
            lambda x: x[0] == self.target_chat_id
        )
        
        # If no language filter, include Ukrainian messages ranking
        if not language:
            # Most Ukrainian messages
            result["most_ukrainian_messages"] = self._find_position_in_ranking(
                full_rankings["most_ukrainian_messages"], 
                lambda x: x[0] == self.target_chat_id
            )
        
        # Most languages
        result["most_languages"] = self._find_position_in_ranking(
            full_rankings["most_languages"], 
            lambda x: x[0] == self.target_chat_id
        )
        
        # Earliest activity
        result["earliest_activity"] = self._find_position_in_ranking(
            full_rankings["earliest_activity"], 
            lambda x: x[0] == self.target_chat_id
        )
        
        # Latest activity
        result["latest_activity"] = self._find_position_in_ranking(
            full_rankings["latest_activity"], 
            lambda x: x[0] == self.target_chat_id
        )
        
        # Average message length
        result["avg_message_length"] = self._find_position_in_ranking(
            full_rankings["highest_avg_message_length"], 
            lambda x: x[0] == self.target_chat_id
        )
        
        return result
        
    def _find_position_in_ranking(self, ranking: List[Any], condition_func) -> Tuple[int, Any]:
        """Find the position of the chat in a ranking and return the position and value"""
        for i, item in enumerate(ranking):
            if condition_func(item):
                if len(item) >= 3:
                    return (i + 1, item[1])  # 1-based position, value is at index 1
                else:
                    return (i + 1, item[1] if len(item) > 1 else None)
                    
        return (0, None)  # Not found
        
    def _generate_full_rankings(self, language: str = None) -> Dict[str, List[Tuple]]:
        """Generate full rankings for all chats (no limit)"""
        # Get total number of chats
        total_chats = len(self.chat_data)
        
        # Generate all rankings using the global top generator with no limit
        if language:
            chat_data = self.global_top_generator._filter_messages_by_language(language)
        else:
            chat_data = self.chat_data
            
        # Get all ranking metrics
        rankings = {
            "most_messages": self.global_top_generator.get_most_messages(limit=total_chats, language=language),
            "most_message_length": self.global_top_generator.get_most_message_length(limit=total_chats, language=language),
            "most_unique_users": self.global_top_generator.get_most_unique_users(limit=total_chats, language=language),
            "earliest_activity": self.global_top_generator.get_earliest_activity_chats(limit=total_chats, language=language),
            "latest_activity": self.global_top_generator.get_latest_activity_chats(limit=total_chats, language=language),
            "highest_avg_message_length": self.global_top_generator.get_highest_avg_message_length(limit=total_chats, language=language),
            "most_languages": self.global_top_generator.get_most_languages(limit=total_chats),
        }
        
        if not language:
            rankings["most_ukrainian_messages"] = self.global_top_generator.get_most_ukrainian_messages(limit=total_chats)
            
        return rankings