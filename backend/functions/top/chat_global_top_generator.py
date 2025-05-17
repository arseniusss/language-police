from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime
from middlewares.database.models import User, ChatMessage

class ChatGlobalTopGenerator:
    """Generate top statistics for chats (comparing chats instead of users)"""
    
    def __init__(self, users: List[User]):
        self.users = users
        # Dictionary to store aggregated chat data
        self.chat_data = self._aggregate_chat_data()
        
    def _aggregate_chat_data(self) -> Dict[str, Dict[str, Any]]:
        """Aggregate data for all chats from user histories"""
        chat_data = {}
        
        # First pass: collect basic data about each chat
        for user in self.users:
            for chat_id, messages in user.chat_history.items():
                if chat_id not in chat_data:
                    chat_data[chat_id] = {
                        "total_messages": 0,
                        "total_length": 0,
                        "users": set(),
                        "earliest_timestamp": None,
                        "latest_timestamp": None,
                        "language_counts": defaultdict(int),
                        "ukrainian_messages": 0,
                    }
                
                # Add this user to chat's user set
                chat_data[chat_id]["users"].add(user.user_id)
                
                # Process each message
                for msg in messages:
                    chat_data[chat_id]["total_messages"] += 1
                    chat_data[chat_id]["total_length"] += len(msg.content)
                    
                    # Update timestamps
                    if (chat_data[chat_id]["earliest_timestamp"] is None or 
                        msg.timestamp < chat_data[chat_id]["earliest_timestamp"]):
                        chat_data[chat_id]["earliest_timestamp"] = msg.timestamp
                        
                    if (chat_data[chat_id]["latest_timestamp"] is None or 
                        msg.timestamp > chat_data[chat_id]["latest_timestamp"]):
                        chat_data[chat_id]["latest_timestamp"] = msg.timestamp
                    
                    # Count languages
                    if msg.analysis_result:
                        top_lang = msg.analysis_result[0]  # First result is highest probability
                        if top_lang["prob"] > 0.5:
                            chat_data[chat_id]["language_counts"][top_lang["lang"]] += 1
                            
                            # Count Ukrainian messages
                            if top_lang["lang"] == "uk" and top_lang["prob"] > 0.5:
                                chat_data[chat_id]["ukrainian_messages"] += 1
        
        # Second pass: calculate averages and other derived metrics
        for chat_id, data in chat_data.items():
            data["unique_users"] = len(data["users"])
            data["avg_message_length"] = (data["total_length"] / data["total_messages"] 
                                         if data["total_messages"] > 0 else 0)
            data["unique_languages"] = len(data["language_counts"])
            
        return chat_data
    
    def _filter_messages_by_language(self, language: str) -> Dict[str, Dict[str, Any]]:
        """Filter chat data to only include messages in the specified language"""
        filtered_data = {}
        
        for user in self.users:
            for chat_id, messages in user.chat_history.items():
                if chat_id not in filtered_data:
                    filtered_data[chat_id] = {
                        "total_messages": 0,
                        "total_length": 0,
                        "users": set(),
                        "earliest_timestamp": None,
                        "latest_timestamp": None,
                    }
                
                # Process each message
                for msg in messages:
                    # Only include messages in the specified language
                    is_target_language = False
                    if msg.analysis_result:
                        for lang_data in msg.analysis_result:
                            if lang_data["lang"] == language and lang_data["prob"] > 0.5:
                                is_target_language = True
                                break
                    
                    if is_target_language:
                        filtered_data[chat_id]["total_messages"] += 1
                        filtered_data[chat_id]["total_length"] += len(msg.content)
                        filtered_data[chat_id]["users"].add(user.user_id)
                        
                        # Update timestamps
                        if (filtered_data[chat_id]["earliest_timestamp"] is None or 
                            msg.timestamp < filtered_data[chat_id]["earliest_timestamp"]):
                            filtered_data[chat_id]["earliest_timestamp"] = msg.timestamp
                            
                        if (filtered_data[chat_id]["latest_timestamp"] is None or 
                            msg.timestamp > filtered_data[chat_id]["latest_timestamp"]):
                            filtered_data[chat_id]["latest_timestamp"] = msg.timestamp
        
        # Calculate averages and remove empty chats
        chats_to_remove = []
        for chat_id, data in filtered_data.items():
            if data["total_messages"] == 0:
                chats_to_remove.append(chat_id)
                continue
                
            data["unique_users"] = len(data["users"])
            data["avg_message_length"] = (data["total_length"] / data["total_messages"] 
                                         if data["total_messages"] > 0 else 0)
        
        # Remove chats with no messages in the target language
        for chat_id in chats_to_remove:
            del filtered_data[chat_id]
                
        return filtered_data
    
    def get_most_messages(self, limit: int = 10, language: str = None) -> List[Tuple[str, int, int]]:
        """Get chats with the most messages"""
        if language:
            chat_data = self._filter_messages_by_language(language)
        else:
            chat_data = self.chat_data
        
        chat_messages = [(chat_id, data["total_messages"], data["unique_users"]) 
                         for chat_id, data in chat_data.items() if data["total_messages"] > 0]
        
        # Sort by message count in descending order
        return sorted(chat_messages, key=lambda x: x[1], reverse=True)[:limit]
    
    def get_most_message_length(self, limit: int = 10, language: str = None) -> List[Tuple[str, int, int]]:
        """Get chats with the most total message length"""
        if language:
            chat_data = self._filter_messages_by_language(language)
        else:
            chat_data = self.chat_data
        
        chat_lengths = [(chat_id, data["total_length"], data["unique_users"]) 
                       for chat_id, data in chat_data.items() if data["total_length"] > 0]
        
        # Sort by length in descending order
        return sorted(chat_lengths, key=lambda x: x[1], reverse=True)[:limit]
    
    def get_most_unique_users(self, limit: int = 10, language: str = None) -> List[Tuple[str, int, int]]:
        """Get chats with the most unique users contributing messages"""
        if language:
            chat_data = self._filter_messages_by_language(language)
        else:
            chat_data = self.chat_data
        
        chat_users = [(chat_id, data["unique_users"], data["total_messages"]) 
                      for chat_id, data in chat_data.items() if data["unique_users"] > 0]
        
        # Sort by unique users in descending order
        return sorted(chat_users, key=lambda x: x[1], reverse=True)[:limit]
    
    def get_most_ukrainian_messages(self, limit: int = 10) -> List[Tuple[str, int, int]]:
        """Get chats with the most Ukrainian messages (confidence > 0.5)"""
        ukrainian_counts = [(chat_id, data["ukrainian_messages"], data["unique_users"]) 
                           for chat_id, data in self.chat_data.items() if data["ukrainian_messages"] > 0]
        
        # Sort by Ukrainian message count in descending order
        return sorted(ukrainian_counts, key=lambda x: x[1], reverse=True)[:limit]
    
    def get_earliest_activity_chats(self, limit: int = 10, language: str = None) -> List[Tuple[str, str, int]]:
        """Get chats with the earliest recorded messages"""
        if language:
            chat_data = self._filter_messages_by_language(language)
        else:
            chat_data = self.chat_data
            
        chats_with_timestamps = [(chat_id, data["earliest_timestamp"], data["unique_users"]) 
                                for chat_id, data in chat_data.items() if data["earliest_timestamp"]]
        
        # Sort by timestamp in ascending order (oldest first)
        return sorted(chats_with_timestamps, key=lambda x: x[1])[:limit]
    
    def get_latest_activity_chats(self, limit: int = 10, language: str = None) -> List[Tuple[str, str, int]]:
        """Get chats with the latest recorded messages"""
        if language:
            chat_data = self._filter_messages_by_language(language)
        else:
            chat_data = self.chat_data
            
        chats_with_timestamps = [(chat_id, data["latest_timestamp"], data["unique_users"]) 
                                for chat_id, data in chat_data.items() if data["latest_timestamp"]]
        
        # Sort by timestamp in descending order (newest first)
        return sorted(chats_with_timestamps, key=lambda x: x[1], reverse=True)[:limit]
    
    def get_highest_avg_message_length(self, limit: int = 10, language: str = None) -> List[Tuple[str, float, int]]:
        """Get chats with the highest average message length"""
        if language:
            chat_data = self._filter_messages_by_language(language)
        else:
            chat_data = self.chat_data
            
        chat_avgs = [(chat_id, data["avg_message_length"], data["unique_users"]) 
                    for chat_id, data in chat_data.items() if data["avg_message_length"] > 0]
        
        # Sort by average length in descending order
        return sorted(chat_avgs, key=lambda x: x[1], reverse=True)[:limit]
    
    def get_most_languages(self, limit: int = 10) -> List[Tuple[str, int, int]]:
        """Get chats with the most unique languages used"""
        chat_languages = [(chat_id, data["unique_languages"], data["unique_users"]) 
                         for chat_id, data in self.chat_data.items() if data["unique_languages"] > 0]
        
        # Sort by language count in descending order
        return sorted(chat_languages, key=lambda x: x[1], reverse=True)[:limit]
    
    def get_top_languages_overall(self, limit: int = 10) -> List[Tuple[str, int, str]]:
        """Get the most used languages across all chats"""
        language_counts = defaultdict(int)
        
        for data in self.chat_data.values():
            for lang, count in data["language_counts"].items():
                language_counts[lang] += count
                
        # Get language display names from helper function
        from backend.functions.helpers.get_lang_display import get_language_display
        
        # Sort by count in descending order and include display name
        return [(lang, count, get_language_display(lang)) 
                for lang, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True)
                if count > 0][:limit]
    
    def generate_top_report(self, limit: int = 10, language: str = None) -> Dict[str, Any]:
        """Generate a comprehensive chat top report"""
        report = {
            "most_messages": self.get_most_messages(limit, language),
            "most_message_length": self.get_most_message_length(limit, language),
            "most_unique_users": self.get_most_unique_users(limit, language),
            "earliest_activity": self.get_earliest_activity_chats(limit, language),
            "latest_activity": self.get_latest_activity_chats(limit, language),
            "highest_avg_message_length": self.get_highest_avg_message_length(limit, language),
            "most_languages": self.get_most_languages(limit),
            "top_languages": self.get_top_languages_overall(limit),
        }
        
        if not language:
            report["most_ukrainian_messages"] = self.get_most_ukrainian_messages(limit)
        else:
            report["language_filter"] = language
            
        return report