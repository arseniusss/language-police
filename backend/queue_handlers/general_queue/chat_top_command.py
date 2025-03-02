import logging
from middlewares.database.db import database
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import TelegramQueueMessageType
from backend.functions.top.top_generator import ChatTopGenerator
from settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

async def handle_chat_top_command(message_data: dict):
    logger.info(f"Handling CHAT_TOP_COMMAND_TG message:\n{message_data}")
    user_id = message_data.get("user_id", 0)
    chat_id = message_data.get("chat_id", "")
    message_id = message_data.get("message_id", "")
    
    # Get chat from database to find users
    chat = await database.get_chat(int(chat_id))
    
    if not chat or not chat.users:
        top_stats = "No users found in this chat!"
    else:
        # Get all users in chat
        users = []
        for user_id in chat.users:
            user = await database.get_user(user_id)
            if user:
                users.append(user)
        
        if not users:
            top_stats = "No users with message history found in this chat!"
        else:
            # Generate top stats for the chat
            top_generator = ChatTopGenerator(users, str(chat_id))
            top_data = top_generator.generate_top_report()
            
            # Format the report
            top_stats = format_top_report(top_data)
    
    response_data = {
        "message_type": TelegramQueueMessageType.CHAT_TOP_COMMAND_ANSWER,
        "chat_id": chat_id,
        "user_id": user_id,
        "top_stats": top_stats,
    }

    await rabbitmq_manager.store_result(settings.RABBITMQ_TELEGRAM_QUEUE, str(chat_id) + '.' + str(message_id), response_data)

def format_top_report(top_data):
    report = "📊 Chat Top Statistics 📊\n\n"
    
    # Most messages
    report += "👑 Most Messages:\n"
    for i, (user_id, name, count) in enumerate(top_data["most_messages"], 1):
        report += f"{i}. {name}: {count} messages\n"
    report += "\n"
    
    # Most message length
    report += "📏 Most Total Message Length:\n"
    for i, (user_id, name, length) in enumerate(top_data["most_message_length"], 1):
        report += f"{i}. {name}: {length} characters\n"
    report += "\n"
    
    # Most Ukrainian messages
    report += "🇺🇦 Most Ukrainian Messages:\n"
    for i, (user_id, name, count) in enumerate(top_data["most_ukrainian_messages"], 1):
        report += f"{i}. {name}: {count} messages\n"
    report += "\n"
    
    # Earliest messages
    report += "🕰️ Earliest Messages:\n"
    for i, (user_id, name, timestamp) in enumerate(top_data["earliest_message_users"], 1):
        report += f"{i}. {name}: {timestamp}\n"
    report += "\n"
    
    # Latest messages
    report += "🆕 Latest Messages:\n"
    for i, (user_id, name, timestamp) in enumerate(top_data["latest_message_users"], 1):
        report += f"{i}. {name}: {timestamp}\n"
    report += "\n"
    
    # Highest average message length
    report += "📊 Highest Average Message Length:\n"
    for i, (user_id, name, avg_length) in enumerate(top_data["highest_avg_message_length"], 1):
        report += f"{i}. {name}: {avg_length:.2f} characters\n"
    
    return report