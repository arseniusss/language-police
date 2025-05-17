from typing import List, Dict, Any, Optional, Tuple
from middlewares.database.models import User, ChatMessage
from backend.functions.top.top_generator import TopGenerator, ChatTopGenerator, GlobalTopGenerator

class SpecificUserRankingGenerator:
    """Base class for finding a specific user's ranking in statistics"""
    
    def __init__(self, users: List[User], target_user_id: int):
        self.users = users
        self.target_user_id = target_user_id
        
    def get_user_rankings(self, language: str = None) -> Dict[str, Tuple[int, Any]]:
        """Get the user's position in various rankings
        
        Returns a dictionary with keys being the ranking type and values being tuples of
        (position, value) where position is the 1-based position of the user in the ranking
        """
        # Generate full ranking data (no limit)
        full_rankings = self._generate_full_rankings(language)
        
        # Find target user's position in each ranking
        result = {}
        
        # Most messages
        result["most_messages"] = self._find_position_in_ranking(
            full_rankings["most_messages"], 
            lambda x: x[0] == self.target_user_id
        )
        
        # Most message length
        result["most_message_length"] = self._find_position_in_ranking(
            full_rankings["most_message_length"], 
            lambda x: x[0] == self.target_user_id
        )
        
        # If no language filter, include Ukrainian messages ranking
        if not language:
            # Most Ukrainian messages
            result["most_ukrainian_messages"] = self._find_position_in_ranking(
                full_rankings["most_ukrainian_messages"], 
                lambda x: x[0] == self.target_user_id
            )
        
        # Earliest message
        result["earliest_message"] = self._find_position_in_ranking(
            full_rankings["earliest_message"], 
            lambda x: x[0] == self.target_user_id
        )
        
        # Latest message
        result["latest_message"] = self._find_position_in_ranking(
            full_rankings["latest_message"], 
            lambda x: x[0] == self.target_user_id
        )
        
        # Avg message length
        result["avg_message_length"] = self._find_position_in_ranking(
            full_rankings["avg_message_length"], 
            lambda x: x[0] == self.target_user_id
        )
        
        return result
    
    def _find_position_in_ranking(self, ranking: List[Any], condition_func) -> Tuple[int, Any]:
        """Find the position of the user in a ranking and return the position and value"""
        for i, item in enumerate(ranking):
            if condition_func(item):
                return (i + 1, item[2])  # 1-based position, value is at index 2
        
        return (0, None)  # Not found
        
    def _generate_full_rankings(self, language: str = None) -> Dict[str, List[Tuple]]:
        """Generate full rankings (no limit)"""
        raise NotImplementedError("Subclasses must implement this method")


class SpecificUserChatRankingGenerator(SpecificUserRankingGenerator):
    """Find a specific user's ranking in chat-based statistics"""
    
    def __init__(self, users: List[User], chat_id: str, target_user_id: int):
        super().__init__(users, target_user_id)
        self.chat_id = chat_id
        self.top_generator = ChatTopGenerator(users, chat_id)
    
    def _generate_full_rankings(self, language: str = None) -> Dict[str, List[Tuple]]:
        """Generate full rankings for the chat (no limit)"""
        languages = [language] if language else None
        
        rankings = {
            "most_messages": self.top_generator._get_most_messages(limit=len(self.users), languages=languages),
            "most_message_length": self.top_generator._get_most_message_length(limit=len(self.users), languages=languages),
            "earliest_message": self.top_generator._get_earliest_message_users(limit=len(self.users), languages=languages),
            "latest_message": self.top_generator._get_latest_message_users(limit=len(self.users), languages=languages),
            "avg_message_length": self.top_generator._get_avg_message_length(limit=len(self.users), languages=languages)
        }
        
        if not language:
            rankings["most_ukrainian_messages"] = self.top_generator._get_most_ukrainian_messages(limit=len(self.users))
            
        return rankings


class SpecificUserGlobalRankingGenerator(SpecificUserRankingGenerator):
    """Find a specific user's ranking in global statistics"""
    
    def __init__(self, users: List[User], target_user_id: int):
        super().__init__(users, target_user_id)
        self.top_generator = GlobalTopGenerator(users)
    
    def _generate_full_rankings(self, language: str = None) -> Dict[str, List[Tuple]]:
        """Generate full rankings globally (no limit)"""
        languages = [language] if language else None
        
        rankings = {
            "most_messages": self.top_generator._get_most_messages(limit=len(self.users), languages=languages),
            "most_message_length": self.top_generator._get_most_message_length(limit=len(self.users), languages=languages),
            "earliest_message": self.top_generator._get_earliest_message_users(limit=len(self.users), languages=languages),
            "latest_message": self.top_generator._get_latest_message_users(limit=len(self.users), languages=languages),
            "avg_message_length": self.top_generator._get_avg_message_length(limit=len(self.users), languages=languages)
        }
        
        if not language:
            rankings["most_ukrainian_messages"] = self.top_generator._get_most_ukrainian_messages(limit=len(self.users))
            
        return rankings