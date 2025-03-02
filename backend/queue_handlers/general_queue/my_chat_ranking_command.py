import logging
from middlewares.database.db import database
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import TelegramQueueMessageType
from backend.functions.top.specific_user_ranking import SpecificUserChatRankingGenerator
from settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

async def handle_my_chat_ranking_command(message_data: dict):
    logger.info(f"Handling MY_CHAT_RANKING_COMMAND_TG message:\n{message_data}")
    user_id = message_data.get("user_id", 0)
    chat_id = message_data.get("chat_id", "")
    message_id = message_data.get("message_id", "")
    
    # Get chat from database to find users
    chat = await database.get_chat(int(chat_id))
    
    if not chat or not chat.users:
        ranking_stats = "No users found in this chat!"
    else:
        # Get all users in chat
        users = []
        for chat_user_id in chat.users:
            user = await database.get_user(chat_user_id)
            if user:
                users.append(user)
        
        if not users:
            ranking_stats = "No users with message history found in this chat!"
        else:
            # Generate user ranking stats
            user_ranking_generator = SpecificUserChatRankingGenerator(users, str(chat_id), int(user_id))
            rankings = user_ranking_generator.get_user_rankings()
            
            # Format the report
            ranking_stats = format_ranking_report(rankings)
    
    response_data = {
        "message_type": TelegramQueueMessageType.MY_CHAT_RANKING_COMMAND_ANSWER,
        "chat_id": chat_id,
        "user_id": user_id,
        "ranking_stats": ranking_stats,
    }

    await rabbitmq_manager.store_result(settings.RABBITMQ_TELEGRAM_QUEUE, str(chat_id) + '.' + str(message_id), response_data)

def format_ranking_report(rankings):
    report = "🏆 Your Rankings in Chat 🏆\n\n"
    
    # Most messages
    msg_pos, msg_count = rankings.get("most_messages", (0, 0))
    if msg_pos > 0:
        report += f"Messages Count: #{msg_pos} with {msg_count} messages\n\n"
    else:
        report += "Messages Count: No ranking\n\n"
    
    # Most message length
    len_pos, total_len = rankings.get("most_message_length", (0, 0))
    if len_pos > 0:
        report += f"Total Message Length: #{len_pos} with {total_len} characters\n\n"
    else:
        report += "Total Message Length: No ranking\n\n"
    
    # Most Ukrainian messages
    ua_pos, ua_count = rankings.get("most_ukrainian_messages", (0, 0))
    if ua_pos > 0:
        report += f"Ukrainian Messages: #{ua_pos} with {ua_count} messages\n\n"
    else:
        report += "Ukrainian Messages: No ranking\n\n"
    
    # Earliest message
    early_pos, early_time = rankings.get("earliest_message", (0, ""))
    if early_pos > 0:
        report += f"Earliest Message: #{early_pos} at {early_time}\n\n"
    else:
        report += "Earliest Message: No ranking\n\n"
    
    # Latest message
    late_pos, late_time = rankings.get("latest_message", (0, ""))
    if late_pos > 0:
        report += f"Latest Message: #{late_pos} at {late_time}\n\n"
    else:
        report += "Latest Message: No ranking\n\n"
    
    # Avg message length
    avg_pos, avg_len = rankings.get("avg_message_length", (0, 0.0))
    if avg_pos > 0:
        report += f"Average Message Length: #{avg_pos} with {avg_len:.2f} characters\n\n"
    else:
        report += "Average Message Length: No ranking\n\n"
    
    return report