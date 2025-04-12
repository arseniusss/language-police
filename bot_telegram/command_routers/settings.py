import logging
from datetime import timedelta
from aiogram import types, Router, F
from aiogram.filters.command import Command
from aiogram.filters.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from middlewares.database.db import database
from middlewares.database.models import Chat, ChatSettings, ModerationRule, RuleCondition, Restriction, RestrictionType, RuleConditionType, ConditionRelationType

settings_router = Router(name='settings_router')
logger = logging.getLogger()

class SettingsStates(StatesGroup):
    main_menu = State()
    waiting_chat_selection = State()  # For private chat interaction
    allowed_languages = State()
    analysis_frequency = State()
    min_message_length = State()
    max_message_length = State()
    new_members_min_messages = State()
    new_rule_name = State()

    # Moderation rules states
    moderation_rules_list = State()
    edit_rule = State()
    new_rule_message = State()
    new_rule_restriction_type = State()
    new_rule_restriction_justification = State()
    new_rule_restriction_duration = State()
    new_rule_condition_type = State()
    new_rule_condition_value = State()
    new_rule_notify_user = State()
    new_rule_add_another_condition = State()
    new_rule_condition_relation_type = State()
    new_rule_condition_field = State()

# Helper classes for organizing conditions and restrictions data
# Add these new classes at the top of the file with other helper classes

class ConditionField:
    """Defines a field for a condition with prompt, type, and validation"""
    def __init__(self, name: str, prompt: str, field_type: type, required: bool = True, 
                 min_value: float = None, max_value: float = None):
        self.name = name
        self.prompt = prompt
        self.field_type = field_type
        self.required = required
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, value: str):
        """Validate the value for this field"""
        try:
            if self.field_type == int:
                converted = int(value)
            elif self.field_type == float:
                converted = float(value)
            elif self.field_type == str:
                converted = value
            else:
                raise ValueError(f"Unsupported field type: {self.field_type}")
            
            # Check min/max if applicable
            if (self.min_value is not None and converted < self.min_value) or \
               (self.max_value is not None and converted > self.max_value):
                min_str = str(self.min_value) if self.min_value is not None else "-∞"
                max_str = str(self.max_value) if self.max_value is not None else "∞"
                raise ValueError(f"Value must be between {min_str} and {max_str}.")
                
            return converted
        except ValueError as e:
            if "could not convert" in str(e):
                raise ValueError(f"Please enter a valid {self.field_type.__name__}.")
            raise e

class ConditionTypeConfig:
    """Configuration for a specific condition type"""
    def __init__(self, fields: list[ConditionField], description: str = ""):
        self.fields = fields
        self.description = description

# Updated ConditionInputHelper with multi-field support
class ConditionInputHelper:
    # Define configurations for each condition type
    CONDITION_CONFIGS = {
        RuleConditionType.SINGLE_MESSAGE_LANGUAGE_CONFIDENCE.value: ConditionTypeConfig(
            fields=[
                ConditionField(
                    "language", 
                    "Enter the language code to check for (e.g., en, uk, ru):", 
                    str
                ),
                ConditionField(
                    "threshold", 
                    "Enter the minimum confidence threshold for language detection (0.0-1.0):", 
                    float, 
                    min_value=0.0, 
                    max_value=1.0
                )
            ],
            description=("This condition checks if a message is detected in a specific language "
                         "with confidence above the threshold. For example, 0.8 means the system "
                         "is at least 80% confident about the language detection.")
        ),
        RuleConditionType.SINGLE_MESSAGE_CONFIDENCE_NOT_IN_ALLOWED_LANGUAGES.value: ConditionTypeConfig(
            fields=[
                ConditionField(
                    "threshold", 
                    "Enter the threshold for detection as a non-allowed language (0.0-1.0):", 
                    float, 
                    min_value=0.0, 
                    max_value=1.0
                )
            ],
            description=("This condition triggers when a message is detected as a language not in "
                         "the allowed list with confidence above the threshold.")
        ),
        RuleConditionType.PREVIOUS_RESTRICTION_TYPE_COUNT.value: ConditionTypeConfig(
            fields=[
                ConditionField(
                    "restriction_type", 
                    "Enter restriction types to count (comma-separated, e.g. warning,timeout or 'any' for all types):", 
                    str
                ),
                ConditionField(
                    "count", 
                    "Enter the minimum number of previous restrictions to trigger the rule:", 
                    int, 
                    min_value=1
                )
            ],
            description=("This condition checks if a user has received a specific number of "
                         "previous restrictions of given types. You can specify multiple types separated by commas "
                         "or use 'any' to match all restriction types.")
        ),
        RuleConditionType.PREVIOUS_RESTRICTION_TYPE_TIME_LENGTH.value: ConditionTypeConfig(
            fields=[
                ConditionField(
                    "restriction_type", 
                    "Enter restriction types to check for (comma-separated, e.g. timeout,ban or 'any' for all types):", 
                    str
                ),
                ConditionField(
                    "seconds", 
                    "Enter the cumulative duration in seconds to trigger the rule:", 
                    int, 
                    min_value=1
                ),
                ConditionField(
                    "window_hours", 
                    "Enter the time window in hours to check for restrictions:", 
                    float, 
                    min_value=0.1
                )
            ],
            description=("This condition checks if a user has had a cumulative duration of "
                         "restrictions of specific types within a time window. You can specify multiple types "
                         "separated by commas or use 'any' to match all restriction types.")
        )
    }
    
    @staticmethod
    def validate_field(condition_type: str, field_name: str, value: str):
        """Validate a field value"""
        config = ConditionInputHelper.CONDITION_CONFIGS.get(condition_type)
        if not config:
            return value
        
        for field in config.fields:
            if field.name == field_name:
                # Special handling for restriction_type field
                if field_name == "restriction_type":
                    # Process as a list or "any"
                    if value.strip().lower() == "any":
                        return ["any"]
                    
                    # Split by comma and strip whitespace
                    restriction_types = [rt.strip() for rt in value.split(",")]
                    
                    # Validate each restriction type
                    valid_types = [rt.value for rt in RestrictionType]
                    for rt in restriction_types:
                        if rt not in valid_types and rt != "any":
                            # Try to find a matching restriction type
                            matched = False
                            for valid_type in valid_types:
                                if valid_type.startswith(rt):
                                    matched = True
                                    break
                            
                            if not matched:
                                raise ValueError(f"Invalid restriction type: {rt}. Valid types are: {', '.join(valid_types)} or 'any'")
                    
                    return restriction_types
                else:
                    return field.validate(value)
        
        return value
    
    @staticmethod
    def get_condition_prompt(condition_type: str) -> str:
        """Get the appropriate prompt for a condition type"""
        config = ConditionInputHelper.CONDITION_CONFIGS.get(condition_type)
        if not config:
            return "Enter the value for this condition:"
        
        return config.description
    
    @staticmethod
    def get_field_prompt(condition_type: str, field_index: int) -> tuple:
        """Get the prompt for a specific field of a condition type"""
        config = ConditionInputHelper.CONDITION_CONFIGS.get(condition_type)
        if not config or field_index >= len(config.fields):
            return None, None
        
        field = config.fields[field_index]
        return field.name, field.prompt

    @staticmethod
    def get_fields_count(condition_type: str) -> int:
        """Get the number of fields for a condition type"""
        config = ConditionInputHelper.CONDITION_CONFIGS.get(condition_type)
        if not config:
            return 0
        return len(config.fields)

class RestrictionInputHelper:
    @staticmethod
    def needs_duration(restriction_type: str) -> bool:
        """Check if a restriction type needs duration"""
        logger.info(f"Checking if {restriction_type} needs duration")
        result = restriction_type in [
            RestrictionType.TIMEOUT.value,
            RestrictionType.TEMPORARY_BAN.value
        ]
        logger.info(f"Result: {result}")
        return result
    
    @staticmethod
    def get_duration_prompt(restriction_type: str) -> str:
        """Get the appropriate duration prompt for a restriction type"""
        if restriction_type == RestrictionType.TIMEOUT.value:
            return "Enter the timeout duration in seconds:"
        elif restriction_type == RestrictionType.TEMPORARY_BAN.value:
            return "Enter the ban duration in seconds:"
        else:
            return ""
    
    @staticmethod
    def process_duration(restriction_type: str, value: str) -> float:
        """Process and validate duration value based on restriction type"""
        try:
            duration = float(value)
            if duration <= 0:
                raise ValueError("Duration must be positive.")
            
            # Use the duration directly in seconds
            return duration
        except ValueError:
            raise ValueError("Please enter a valid positive number.")

async def is_user_admin(chat_id: int, user_id: int) -> bool:
    """Check if user is an admin in the chat"""
    logger.info(f"Checking if user {user_id} is admin in chat {chat_id}")
    chat = await database.get_chat(chat_id)
    if not chat:
        logger.warning(f"Chat {chat_id} not found in database")
        return False
    is_admin = user_id in chat.admins
    logger.info(f"User {user_id} admin status in chat {chat_id}: {is_admin}")
    return is_admin

@settings_router.message(Command("chat_settings"))
async def chat_settings_command(message: types.Message, state: FSMContext):
    logger.info(f"Chat settings command received from user {message.from_user.id} in chat {message.chat.id}")
    
    # Check if in a private chat
    if message.chat.type == "private":
        # If in private chat, show a list of chats the user is admin in
        await show_admin_chats(message, state)
        return
        
    # If in a group chat, check admin status
    is_admin = await is_user_admin(message.chat.id, message.from_user.id)
    
    if not is_admin:
        await message.reply("You need to be an admin to change chat settings. Use /add_admins to sync administrators.")
        logger.warning(f"User {message.from_user.id} attempted to access settings without admin rights in chat {message.chat.id}")
        return
    
    # Get chat info
    chat = await database.get_chat(message.chat.id)
    if not chat:
        await message.reply("Chat not found in database. Please try again later.")
        logger.warning(f"Chat {message.chat.id} not found in database")
        return
    
    # Store chat ID and inform user
    await state.update_data(chat_id=message.chat.id)
    await message.reply("I've sent you the settings menu in a private message.")
    
    try:
        # Send settings menu directly to user's private chat
        builder = InlineKeyboardBuilder()
        builder.button(text="Allowed Languages", callback_data="settings_allowed_languages")
        builder.button(text="Analysis Frequency", callback_data="settings_analysis_frequency")
        builder.button(text="Message Length Limits", callback_data="settings_message_length")
        builder.button(text="Minimum Messages for New Users", callback_data="settings_min_messages")
        builder.button(text="Moderation Rules", callback_data="settings_moderation_rules")
        builder.button(text="Close", callback_data="settings_close")
        builder.adjust(1)  # One button per row
        
        # Send the menu to user's private chat
        await message.bot.send_message(
            message.from_user.id,
            f"Chat Settings for {chat.last_known_name}\n\n"
            f"Current settings:\n"
            f"• Allowed languages: {', '.join(chat.chat_settings.allowed_languages)}\n"
            f"• Analysis frequency: {chat.chat_settings.analysis_frequency}\n"
            f"• Min message length: {chat.chat_settings.min_message_length_for_analysis}\n"
            f"• Max message length: {chat.chat_settings.max_message_length_for_analysis}\n"
            f"• New members min messages: {chat.chat_settings.new_members_min_analyzed_messages}\n"
            f"• Moderation rules: {len(chat.chat_settings.moderation_rules)}\n\n"
            f"Select a setting to modify:",
            reply_markup=builder.as_markup()
        )
        
        # Set state for the private chat
        await state.set_state(SettingsStates.main_menu)
        logger.info(f"Sent settings menu to private chat for user {message.from_user.id}")
        
    except Exception as e:
        # Handle the case where the bot cannot message the user
        await message.reply(
            "I couldn't send you a private message. Please start a conversation with me first by clicking "
            f"this link: https://t.me/{(await message.bot.get_me()).username}"
        )
        logger.error(f"Failed to send settings menu to user {message.from_user.id}: {str(e)}")

async def show_admin_chats(message: types.Message, state: FSMContext):
    """Show a list of chats where the user is an admin"""
    logger.info(f"Showing admin chats for user {message.from_user.id}")
    
    # Check if we have a specific chat ID from deep linking
    start_param = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    
    if start_param.startswith("settings_"):
        chat_id = int(start_param.split("_")[1])
        # Verify admin status
        if await is_user_admin(chat_id, message.from_user.id):
            chat = await database.get_chat(chat_id)
            if chat:
                await show_settings_menu(message, state, chat)
                return
        else:
            await message.reply("You are not an admin in this chat.")
            return
    
    # Find all chats where the user is admin
    admin_chats = []
    async for chat in database.db["chats"].find({}):
        logger.info(f"Checking chat {chat['chat_id']} for admin status")
        logger.info(f"{str(message.from_user.id)} != {chat.get('admins', {})}, {str(message.from_user.id) in chat.get('admins', {})}")
        if str(message.from_user.id) in chat.get("admins", {}):
            admin_chats.append(Chat(**chat))
    
    if not admin_chats:
        await message.reply(
            "You are not an administrator in any chats, or your admin status hasn't been synced yet.\n\n"
            "To sync admin status, use the /add_admins command in the group chat."
        )
        logger.info(f"No admin chats found for user {message.from_user.id}")
        return
    
    builder = InlineKeyboardBuilder()
    for chat in admin_chats:
        builder.button(
            text=chat.last_known_name or f"Chat {chat.chat_id}", 
            callback_data=f"select_chat_{chat.chat_id}"
        )
    builder.adjust(1)
    
    await message.reply(
        "Select a chat to configure its settings:",
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(SettingsStates.waiting_chat_selection)
    logger.info(f"Displayed {len(admin_chats)} admin chats for user {message.from_user.id}")

@settings_router.callback_query(F.data.startswith("select_chat_"), SettingsStates.waiting_chat_selection)
async def select_chat_callback(callback: types.CallbackQuery, state: FSMContext):
    chat_id = int(callback.data.split("_")[2])
    logger.info(f"User {callback.from_user.id} selected chat {chat_id} for settings")
    
    # Verify admin status again
    if not await is_user_admin(chat_id, callback.from_user.id):
        await callback.answer("You are not an admin in this chat anymore.", show_alert=True)
        await callback.message.edit_text("Your admin status has changed. Please try again.")
        await state.clear()
        return
    
    chat = await database.get_chat(chat_id)
    if not chat:
        await callback.answer("Chat not found. It may have been deleted.", show_alert=True)
        await callback.message.edit_text("The selected chat was not found in the database.")
        await state.clear()
        return
    
    await show_settings_menu(callback.message, state, chat)

async def show_settings_menu(message: types.Message, state: FSMContext, chat: Chat):
    """Show the main settings menu for a specific chat"""
    logger.info(f"Showing settings menu for chat {chat.chat_id}")
    
    # Store chat in state
    await state.update_data(chat_id=chat.chat_id)
    
    # Create main menu keyboard
    builder = InlineKeyboardBuilder()
    builder.button(text="Allowed Languages", callback_data="settings_allowed_languages")
    builder.button(text="Analysis Frequency", callback_data="settings_analysis_frequency")
    builder.button(text="Message Length Limits", callback_data="settings_message_length")
    builder.button(text="Minimum Messages for New Users", callback_data="settings_min_messages")
    builder.button(text="Moderation Rules", callback_data="settings_moderation_rules")
    builder.button(text="Close", callback_data="settings_close")
    builder.adjust(1)  # One button per row
    
    await message.edit_text(
        f"Chat Settings for {chat.last_known_name}\n\n"
        f"Current settings:\n"
        f"• Allowed languages: {', '.join(chat.chat_settings.allowed_languages)}\n"
        f"• Analysis frequency: {chat.chat_settings.analysis_frequency}\n"
        f"• Min message length: {chat.chat_settings.min_message_length_for_analysis}\n"
        f"• Max message length: {chat.chat_settings.max_message_length_for_analysis}\n"
        f"• New members min messages: {chat.chat_settings.new_members_min_analyzed_messages}\n"
        f"• Moderation rules: {len(chat.chat_settings.moderation_rules)}\n\n"
        f"Select a setting to modify:",
        reply_markup=builder.as_markup()
    ) if hasattr(message, 'edit_text') else await message.reply(
        f"Chat Settings for {chat.last_known_name}\n\n"
        f"Current settings:\n"
        f"• Allowed languages: {', '.join(chat.chat_settings.allowed_languages)}\n"
        f"• Analysis frequency: {chat.chat_settings.analysis_frequency}\n"
        f"• Min message length: {chat.chat_settings.min_message_length_for_analysis}\n"
        f"• Max message length: {chat.chat_settings.max_message_length_for_analysis}\n"
        f"• New members min messages: {chat.chat_settings.new_members_min_analyzed_messages}\n"
        f"• Moderation rules: {len(chat.chat_settings.moderation_rules)}\n\n"
        f"Select a setting to modify:",
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(SettingsStates.main_menu)

# === ALLOWED LANGUAGES HANDLERS ===
@settings_router.callback_query(F.data == "settings_allowed_languages", SettingsStates.main_menu)
async def cb_allowed_languages(callback: types.CallbackQuery, state: FSMContext):
    # Check admin permissions again
    chat_id = (await state.get_data())['chat_id']
    if not await is_user_admin(chat_id, callback.from_user.id):
        await callback.answer("You need to be an admin to change chat settings.", show_alert=True)
        logger.warning(f"User {callback.from_user.id} attempted to access language settings without admin rights")
        return
        
    logger.info(f"User {callback.from_user.id} accessing language settings for chat {chat_id}")
    chat = await database.get_chat(chat_id)
    
    builder = InlineKeyboardBuilder()
    
    # Common languages with toggle buttons
    common_languages = [
        ("🇺🇦 Ukrainian (uk)", "uk"),
        ("🇬🇧 English (en)", "en"),
        ("🇷🇺 Russian (ru)", "ru"),
        ("🇵🇱 Polish (pl)", "pl"),
        ("🇩🇪 German (de)", "de"),
        ("🇫🇷 French (fr)", "fr")
    ]
    
    for lang_name, lang_code in common_languages:
        is_enabled = lang_code in chat.chat_settings.allowed_languages
        status = "✅" if is_enabled else "❌"
        builder.button(
            text=f"{status} {lang_name}", 
            callback_data=f"lang_toggle_{lang_code}"
        )
    
    builder.button(text="Back to Main Menu", callback_data="settings_back_main")
    builder.adjust(1)  # One button per row
    
    await callback.message.edit_text(
        "Select languages to allow in this chat:\n\n"
        "Users writing in languages not on this list may be warned or restricted "
        "according to your moderation rules.",
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(SettingsStates.allowed_languages)

@settings_router.callback_query(F.data.startswith("lang_toggle_"), SettingsStates.allowed_languages)
async def cb_toggle_language(callback: types.CallbackQuery, state: FSMContext):
    # Check admin permissions again
    chat_id = (await state.get_data())['chat_id']
    if not await is_user_admin(chat_id, callback.from_user.id):
        await callback.answer("You need to be an admin to change chat settings.", show_alert=True)
        logger.warning(f"User {callback.from_user.id} attempted to toggle language without admin rights")
        return
        
    lang_code = callback.data.split("_")[-1]
    logger.info(f"User {callback.from_user.id} toggling language {lang_code} for chat {chat_id}")
    
    chat = await database.get_chat(chat_id)
    
    if lang_code in chat.chat_settings.allowed_languages:
        chat.chat_settings.allowed_languages.remove(lang_code)
        logger.info(f"Removed language {lang_code} from allowed languages")
    else:
        chat.chat_settings.allowed_languages.append(lang_code)
        logger.info(f"Added language {lang_code} to allowed languages")
    
    await database.update_chat(chat_id, {"chat_settings": chat.chat_settings.dict()})
    
    # Refresh the languages menu
    await cb_allowed_languages(callback, state)

# === MODERATION RULES HANDLERS ===
@settings_router.callback_query(F.data == "settings_moderation_rules")
async def cb_moderation_rules(callback: types.CallbackQuery, state: FSMContext):
    # Check admin permissions again
    chat_id = (await state.get_data())['chat_id']
    if not await is_user_admin(chat_id, callback.from_user.id):
        await callback.answer("You need to be an admin to change chat settings.", show_alert=True)
        logger.warning(f"User {callback.from_user.id} attempted to access moderation rules without admin rights")
        return
    
    logger.info(f"User {callback.from_user.id} accessing moderation rules for chat {chat_id}")
    chat = await database.get_chat(chat_id)
    
    builder = InlineKeyboardBuilder()
    
    if chat.chat_settings.moderation_rules:
        for i, rule in enumerate(chat.chat_settings.moderation_rules):
            # Use rule name if available, otherwise use message
            if hasattr(rule, 'name') and rule.name:
                rule_display = rule.name
            else:
                rule_display = rule.message
            
            # Truncate if too long
            rule_display = rule_display[:30] + "..." if len(rule_display) > 30 else rule_display
            
            builder.button(
                text=f"{i+1}. {rule_display}",
                callback_data=f"edit_rule_{i}"
            )
    
    builder.button(text="➕ Add New Rule", callback_data="add_new_rule")
    builder.button(text="Back to Main Menu", callback_data="settings_back_main")
    builder.adjust(1)  # One button per row
    
    message_text = "Moderation Rules:\n\n"
    if not chat.chat_settings.moderation_rules:
        message_text += "No rules configured yet. Add a rule to automatically warn or restrict users based on specific conditions."
    else:
        message_text += "Select a rule to edit or delete, or add a new rule."
    
    await callback.message.edit_text(
        message_text,
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(SettingsStates.moderation_rules_list)

@settings_router.callback_query(F.data == "add_new_rule", SettingsStates.moderation_rules_list)
async def cb_add_new_rule(callback: types.CallbackQuery, state: FSMContext):
    # Check admin permissions again
    chat_id = (await state.get_data())['chat_id']
    if not await is_user_admin(chat_id, callback.from_user.id):
        await callback.answer("You need to be an admin to change chat settings.", show_alert=True)
        logger.warning(f"User {callback.from_user.id} attempted to add a rule without admin rights")
        return
    
    # Initialize empty conditions list
    await state.update_data(rule_conditions=[])
    
    logger.info(f"User {callback.from_user.id} starting to add a new rule for chat {chat_id}")
    await callback.message.edit_text(
        "Please enter a name for this rule (for display purposes only):"
    )
    
    await state.set_state(SettingsStates.new_rule_name)

@settings_router.message(SettingsStates.new_rule_name)
async def process_new_rule_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    chat_id = data['chat_id']
    
    # Check admin status again
    if not await is_user_admin(chat_id, message.from_user.id):
        await message.reply("You no longer have admin permissions for this chat.")
        await state.clear()
        logger.warning(f"User {message.from_user.id} lost admin rights while setting rule name")
        return
    
    # Save the rule name
    await state.update_data(rule_name=message.text)
    logger.info(f"User {message.from_user.id} set rule name: {message.text}")
    
    # Now ask for the message
    await message.reply(
        "Please enter a message that will be shown to users when this rule is triggered:"
    )
    
    await state.set_state(SettingsStates.new_rule_message)

@settings_router.message(SettingsStates.new_rule_message)
async def process_new_rule_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    chat_id = data['chat_id']
    
    # Check admin status again
    if not await is_user_admin(chat_id, message.from_user.id):
        await message.reply("You no longer have admin permissions for this chat.")
        await state.clear()
        logger.warning(f"User {message.from_user.id} lost admin rights while setting rule message")
        return
    
    # Save the rule message
    await state.update_data(rule_message=message.text)
    logger.info(f"User {message.from_user.id} set rule message: {message.text}")
    
    # Ask for restriction type
    builder = InlineKeyboardBuilder()
    for restriction_type in RestrictionType:
        builder.button(
            text=restriction_type.value.capitalize(), 
            callback_data=f"restriction_{restriction_type.value}"
        )
    builder.adjust(1)
    
    await message.reply(
        "Select the type of restriction to apply:",
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(SettingsStates.new_rule_restriction_type)

@settings_router.callback_query(F.data.startswith("restriction_"), SettingsStates.new_rule_restriction_type)
async def cb_restriction_type(callback: types.CallbackQuery, state: FSMContext):
    # Check admin permissions again
    chat_id = (await state.get_data())['chat_id']
    if not await is_user_admin(chat_id, callback.from_user.id):
        await callback.answer("You need to be an admin to change chat settings.", show_alert=True)
        logger.warning(f"User {callback.from_user.id} attempted to set restriction type without admin rights")
        return
        
    callback_data = callback.data.split("_")[1]
    # Make sure the restriction_type is actually a valid enum value
    valid_restriction_types = [rt.value for rt in RestrictionType]
    
    if callback_data not in valid_restriction_types:
        # Find a matching valid restriction type
        for valid_type in valid_restriction_types:
            if valid_type.startswith(callback_data):
                restriction_type = valid_type
                break
        else:
            # If no match, default to warning
            restriction_type = RestrictionType.WARNING.value
            logger.warning(f"Invalid restriction type from callback: {callback_data}. Using {restriction_type} instead.")
    else:
        restriction_type = callback_data
    
    logger.info(f"User {callback.from_user.id} selected restriction type: {restriction_type}")
    await state.update_data(restriction_type=restriction_type)
    
    # Ask for justification message
    await callback.message.edit_text(
        "Enter a message explaining why this restriction was applied (optional):\n\n"
        "This will be included in admin logs and notifications."
    )
    
    await state.set_state(SettingsStates.new_rule_restriction_justification)

@settings_router.message(SettingsStates.new_rule_restriction_justification)
async def process_restriction_justification(message: types.Message, state: FSMContext):
    data = await state.get_data()
    chat_id = data['chat_id']
    restriction_type = data['restriction_type']
    
    # Check admin status again
    if not await is_user_admin(chat_id, message.from_user.id):
        await message.reply("You no longer have admin permissions for this chat.")
        await state.clear()
        logger.warning(f"User {message.from_user.id} lost admin rights while setting restriction justification")
        return
    
    # Save justification
    justification = message.text if message.text != "-" else None  # Allow skipping with "-"
    await state.update_data(restriction_justification=justification)
    
    # If restriction type requires duration, ask for it
    if RestrictionInputHelper.needs_duration(restriction_type):
        prompt = RestrictionInputHelper.get_duration_prompt(restriction_type)
        logger.info(f"Asking for duration for restriction type: {restriction_type}")
        await message.reply(prompt)
        await state.set_state(SettingsStates.new_rule_restriction_duration)
    else:
        # Skip duration step for restriction types that don't need it
        logger.info(f"Skipping duration for restriction type: {restriction_type}")
        await message.reply("Now let's set up the conditions for this rule.")
        await ask_for_condition_type(message, state)

@settings_router.message(SettingsStates.new_rule_restriction_duration)
async def process_restriction_duration(message: types.Message, state: FSMContext):
    data = await state.get_data()
    chat_id = data['chat_id']
    restriction_type = data['restriction_type']
    
    # Check admin status again
    if not await is_user_admin(chat_id, message.from_user.id):
        await message.reply("You no longer have admin permissions for this chat.")
        await state.clear()
        logger.warning(f"User {message.from_user.id} lost admin rights while setting restriction duration")
        return
    
    try:
        # Process duration
        duration_seconds = RestrictionInputHelper.process_duration(restriction_type, message.text)
        await state.update_data(restriction_duration=duration_seconds)
        
        # Move to condition setup
        await message.reply("Now let's set up the conditions for this rule.")
        await ask_for_condition_type(message, state)
        
    except ValueError as e:
        await message.reply(str(e))

async def ask_for_condition_type(message: types.Message, state: FSMContext):
    """Ask the user to select a condition type"""
    builder = InlineKeyboardBuilder()
    for condition_type in RuleConditionType:
        # Simplify the condition name for display
        display_name = condition_type.value.replace("_", " ").capitalize()
        builder.button(
            text=display_name,
            callback_data=f"condition_{condition_type.value}"
        )
    builder.adjust(1)
    
    await message.reply(
        "Select the condition type for this rule:",
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(SettingsStates.new_rule_condition_type)

@settings_router.callback_query(F.data.startswith("condition_"), SettingsStates.new_rule_condition_type)
async def cb_condition_type(callback: types.CallbackQuery, state: FSMContext):
    # Check admin permissions again
    chat_id = (await state.get_data())['chat_id']
    if not await is_user_admin(chat_id, callback.from_user.id):
        await callback.answer("You need to be an admin to change chat settings.", show_alert=True)
        logger.warning(f"User {callback.from_user.id} attempted to set condition type without admin rights")
        return
        
    condition_type = callback.data.split("_", 1)[1]
    await state.update_data(current_condition_type=condition_type, current_condition_fields={}, current_field_index=0)
    logger.info(f"User {callback.from_user.id} selected condition type: {condition_type}")
    
    # Get description for this condition type
    description = ConditionInputHelper.get_condition_prompt(condition_type)
    
    # Get first field prompt
    field_name, field_prompt = ConditionInputHelper.get_field_prompt(condition_type, 0)
    
    if field_name:
        # This is a multi-field condition
        message_text = f"{description}\n\n{field_prompt}"
        await callback.message.edit_text(message_text)
        await state.set_state(SettingsStates.new_rule_condition_field)
    else:
        # Fall back to the old behavior for unknown condition types
        await callback.message.edit_text(description)
        await state.set_state(SettingsStates.new_rule_condition_value)

@settings_router.message(SettingsStates.new_rule_condition_field)
async def process_condition_field(message: types.Message, state: FSMContext):
    data = await state.get_data()
    chat_id = data['chat_id']
    condition_type = data['current_condition_type']
    field_index = data.get('current_field_index', 0)
    fields = data.get('current_condition_fields', {})
    
    # Check admin status again
    if not await is_user_admin(chat_id, message.from_user.id):
        await message.reply("You no longer have admin permissions for this chat.")
        await state.clear()
        logger.warning(f"User {message.from_user.id} lost admin rights while setting condition field")
        return
    
    try:
        # Get current field info
        field_name, _ = ConditionInputHelper.get_field_prompt(condition_type, field_index)
        if not field_name:
            await message.reply("Error: field not found.")
            return
        
        # Validate field value
        validated_value = ConditionInputHelper.validate_field(condition_type, field_name, message.text)
        
        # Store field value
        fields[field_name] = validated_value
        await state.update_data(current_condition_fields=fields)
        
        # Check if we have more fields
        next_field_index = field_index + 1
        total_fields = ConditionInputHelper.get_fields_count(condition_type)
        
        if next_field_index < total_fields:
            # More fields to collect
            next_field_name, next_field_prompt = ConditionInputHelper.get_field_prompt(condition_type, next_field_index)
            await message.reply(next_field_prompt)
            await state.update_data(current_field_index=next_field_index)
        else:
            # All fields collected, create the condition
            condition = {
                "type": condition_type,
                "values": fields,
                "this_chat_only": True
            }
            
            # Add time window for conditions that need it
            if condition_type == RuleConditionType.PREVIOUS_RESTRICTION_TYPE_TIME_LENGTH.value:
                window_hours = fields.get("window_hours", 24)
                condition["time_window"] = str(timedelta(hours=window_hours))
            
            # Add condition to list
            rule_conditions = data.get('rule_conditions', [])
            rule_conditions.append(condition)
            await state.update_data(rule_conditions=rule_conditions)
            
            # Ask if user wants to add another condition
            builder = InlineKeyboardBuilder()
            builder.button(text="Yes, add another condition", callback_data="add_another_condition")
            builder.button(text="No, continue", callback_data="done_with_conditions")
            builder.adjust(1)
            
            await message.reply(
                f"Condition added! Do you want to add another condition?",
                reply_markup=builder.as_markup()
            )
            
            await state.set_state(SettingsStates.new_rule_add_another_condition)
        
    except ValueError as e:
        await message.reply(str(e))

@settings_router.callback_query(F.data == "add_another_condition", SettingsStates.new_rule_add_another_condition)
async def cb_add_another_condition(callback: types.CallbackQuery, state: FSMContext):
    # If user has multiple conditions, ask how they should be related
    data = await state.get_data()
    rule_conditions = data.get('rule_conditions', [])
    
    if len(rule_conditions) == 1:
        # First additional condition, so we need to ask about relation type
        builder = InlineKeyboardBuilder()
        for relation_type in ConditionRelationType:
            builder.button(
                text=relation_type.value.upper(),
                callback_data=f"relation_{relation_type.value}"
            )
        builder.adjust(2)
        
        await callback.message.edit_text(
            "How should multiple conditions be combined?\n\n"
            "• AND: All conditions must be met\n"
            "• OR: Any condition must be met",
            reply_markup=builder.as_markup()
        )
        
        await state.set_state(SettingsStates.new_rule_condition_relation_type)
    else:
        # Already have the relation type, just add another condition
        await ask_for_condition_type(callback.message, state)

@settings_router.callback_query(F.data.startswith("relation_"), SettingsStates.new_rule_condition_relation_type)
async def cb_condition_relation(callback: types.CallbackQuery, state: FSMContext):
    relation_type = callback.data.split("_")[1]
    await state.update_data(condition_relation=relation_type)
    
    # Now ask for the next condition
    await ask_for_condition_type(callback.message, state)

@settings_router.callback_query(F.data == "done_with_conditions", SettingsStates.new_rule_add_another_condition)
async def cb_done_with_conditions(callback: types.CallbackQuery, state: FSMContext):
    # Proceed to asking if user should be notified
    builder = InlineKeyboardBuilder()
    builder.button(text="Yes", callback_data="notify_yes")
    builder.button(text="No", callback_data="notify_no")
    builder.adjust(2)
    
    await callback.message.edit_text(
        "Should the user be notified privately when this rule is triggered?\n\n"
        "If enabled, the message will be sent to the user's private messages instead of in the group chat.",
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(SettingsStates.new_rule_notify_user)

@settings_router.callback_query(F.data.startswith("notify_"), SettingsStates.new_rule_notify_user)
async def cb_notify_user(callback: types.CallbackQuery, state: FSMContext):
    # Check admin permissions again
    data = await state.get_data()
    chat_id = data['chat_id']
    if not await is_user_admin(chat_id, callback.from_user.id):
        await callback.answer("You need to be an admin to change chat settings.", show_alert=True)
        logger.warning(f"User {callback.from_user.id} attempted to set notification preference without admin rights")
        return
        
    notify = callback.data == "notify_yes"
    logger.info(f"User {callback.from_user.id} set notification preference: {notify}")
    
    # Get all the rule data
    rule_name = data['rule_name']
    rule_message = data['rule_message']
    restriction_type = data['restriction_type']
    restriction_justification = data.get('restriction_justification')
    restriction_duration = data.get('restriction_duration')
    rule_conditions = data.get('rule_conditions', [])
    condition_relation = data.get('condition_relation', ConditionRelationType.AND.value)
    
    # Make sure restriction_type is a valid value from RestrictionType enum
    # Log the received restriction_type to help debug
    logger.info(f"Restriction type from state: {restriction_type}")
    
    # Ensure restriction_type is one of the valid enum values
    valid_restriction_types = [rt.value for rt in RestrictionType]
    if restriction_type not in valid_restriction_types:
        # Try to find a matching restriction type
        for valid_type in valid_restriction_types:
            if valid_type.startswith(restriction_type):
                restriction_type = valid_type
                break
        else:
            # If no match found, default to warning
            logger.warning(f"Invalid restriction type: {restriction_type}. Using 'warning' instead.")
            restriction_type = RestrictionType.WARNING.value
    
    # Create the restriction
    restriction = Restriction(
        restriction_type=restriction_type,
        restriction_justification_message=restriction_justification,
        duration_seconds=restriction_duration
    )
    
    # Convert condition dictionaries to RuleCondition objects
    conditions = []
    for cond_dict in rule_conditions:
        time_window = None
        if "time_window" in cond_dict:
            # Convert string representation back to timedelta
            time_window_str = cond_dict.pop("time_window")
            # Parse the string, assuming format like "1 day, 0:00:00"
            days = 0
            hours = 0
            if "day" in time_window_str:
                days_part = time_window_str.split(",")[0]
                days = int(days_part.split()[0])
                time_part = time_window_str.split(",")[1].strip()
                hours = int(time_part.split(":")[0])
            else:
                time_parts = time_window_str.split(":")
                hours = int(time_parts[0])
            
            time_window = timedelta(days=days, hours=hours)
        
        conditions.append(RuleCondition(
            type=cond_dict["type"],
            values=cond_dict["values"],
            this_chat_only=cond_dict.get("this_chat_only", True),
            time_window=time_window,
            extra_data=cond_dict.get("extra_data")
        ))
    
    # Create the new rule
    new_rule = ModerationRule(
        name = rule_name,
        conditions=conditions,
        condition_relation=condition_relation,
        restriction=restriction,
        message=rule_message,
        notify_user=notify
    )
    
    # Add rule to chat settings
    chat = await database.get_chat(chat_id)
    chat.chat_settings.moderation_rules.append(new_rule)
    
    await database.update_chat(chat_id, {"chat_settings": chat.chat_settings.dict()})
    logger.info(f"Added new moderation rule to chat {chat_id}")
    
    # Show summary of the created rule
    conditions_summary = []
    for i, cond in enumerate(conditions):
        condition_desc = f"{i+1}. {format_condition_type(cond.type)}"
        conditions_summary.append(condition_desc)
        
        if cond.values:
            # Format values for readability based on condition type
            if cond.type == RuleConditionType.SINGLE_MESSAGE_LANGUAGE_CONFIDENCE:
                language_code = cond.values.get('language', 'N/A')
                # Get human-readable language name if available
                from backend.functions.helpers.get_lang_display import get_language_display
                language_display = get_language_display(language_code)
                
                conditions_summary.append(f"   • Language: {language_display}")
                conditions_summary.append(f"   • Confidence threshold: {cond.values.get('threshold', 'N/A')}")
            
            elif cond.type == RuleConditionType.SINGLE_MESSAGE_CONFIDENCE_NOT_IN_ALLOWED_LANGUAGES:
                conditions_summary.append(f"   • Confidence threshold: {cond.values.get('threshold', 'N/A')}")
            
            elif cond.type == RuleConditionType.PREVIOUS_RESTRICTION_TYPE_COUNT:
                restriction_types = cond.values.get('restriction_type', ['any'])
                if isinstance(restriction_types, str):
                    restriction_types = [restriction_types]  # Convert to list for backward compatibility
                    
                types_display = ", ".join(restriction_types) if restriction_types != ["any"] else "any"
                conditions_summary.append(f"   • Restriction types: {types_display}")
                conditions_summary.append(f"   • Count: {cond.values.get('count', 'N/A')}")
            
            elif cond.type == RuleConditionType.PREVIOUS_RESTRICTION_TYPE_TIME_LENGTH:
                restriction_types = cond.values.get('restriction_type', ['any'])
                if isinstance(restriction_types, str):
                    restriction_types = [restriction_types]  # Convert to list for backward compatibility
                    
                types_display = ", ".join(restriction_types) if restriction_types != ["any"] else "any"
                conditions_summary.append(f"   • Restriction types: {types_display}")
                conditions_summary.append(f"   • Cumulative duration: {cond.values.get('seconds', 'N/A')} seconds")
                conditions_summary.append(f"   • Within time window: {cond.values.get('window_hours', 'N/A')} hours")
            
            else:
                # Generic fallback for unknown condition types
                for key, val in cond.values.items():
                    conditions_summary.append(f"   • {key}: {val}")
    
    restriction_details = [
        f"Type: {restriction_type}",
    ]
    
    if restriction_justification:
        restriction_details.append(f"Justification: {restriction_justification}")
        
    if restriction_duration:
        restriction_details.append(f"Duration: {restriction_duration} seconds")
    
    relation_display = "ALL conditions must be met" if condition_relation == ConditionRelationType.AND.value else "ANY condition must be met"
    
    await callback.message.edit_text(
        "✅ New moderation rule has been added successfully!\n\n"
        f"Name: {rule_name}\n\n"
        f"Message: {rule_message}\n\n"
        f"Restriction:\n" + "\n".join(restriction_details) + "\n\n"
        f"Notify user privately: {'Yes' if notify else 'No'}\n\n"
        f"Conditions ({relation_display}):\n" + "\n".join(conditions_summary)
    )
    
    # Add a button to return to rules list
    builder = InlineKeyboardBuilder()
    builder.button(text="Back to Rules List", callback_data="settings_moderation_rules")
    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())

# === ANALYSIS FREQUENCY HANDLERS ===
@settings_router.callback_query(F.data == "settings_analysis_frequency", SettingsStates.main_menu)
async def cb_analysis_frequency(callback: types.CallbackQuery, state: FSMContext):
    # Check admin permissions again
    chat_id = (await state.get_data())['chat_id']
    if not await is_user_admin(chat_id, callback.from_user.id):
        await callback.answer("You need to be an admin to change chat settings.", show_alert=True)
        logger.warning(f"User {callback.from_user.id} attempted to access analysis frequency without admin rights")
        return
    
    logger.info(f"User {callback.from_user.id} accessing analysis frequency settings for chat {chat_id}")
    await callback.message.edit_text(
        "Enter the analysis frequency (0.05-1.0):\n\n"
        "This determines what fraction of messages will be analyzed. "
        "For example, 0.1 means 10% of messages will be analyzed, while "
        "1.0 means every message will be analyzed."
    )
    
    await state.set_state(SettingsStates.analysis_frequency)

@settings_router.message(SettingsStates.analysis_frequency)
async def process_analysis_frequency(message: types.Message, state: FSMContext):
    data = await state.get_data()
    chat_id = data['chat_id']
    
    # Check admin status again
    if not await is_user_admin(chat_id, message.from_user.id):
        await message.reply("You no longer have admin permissions for this chat.")
        await state.clear()
        logger.warning(f"User {message.from_user.id} lost admin rights while setting analysis frequency")
        return
    
    try:
        freq = float(message.text)
        if 0.05 <= freq <= 1.0:
            chat = await database.get_chat(chat_id)
            
            chat.chat_settings.analysis_frequency = freq
            await database.update_chat(chat_id, {"chat_settings": chat.chat_settings.dict()})
            logger.info(f"Updated analysis frequency to {freq} for chat {chat_id}")
            
            await message.reply(f"Analysis frequency updated to {freq}")
            
            # Return to main menu
            builder = InlineKeyboardBuilder()
            builder.button(text="Back to Main Menu", callback_data="settings_back_main")
            await message.reply("What would you like to do next?", reply_markup=builder.as_markup())
        else:
            await message.reply("Value must be between 0.05 and 1.0. Please try again.")
            logger.warning(f"Invalid analysis frequency: {freq} - not in range 0.05-1.0")
    except ValueError:
        await message.reply("Please enter a valid number between 0.05 and 1.0.")
        logger.warning(f"Invalid analysis frequency: {message.text} - not a number")

# === MESSAGE LENGTH HANDLERS ===
@settings_router.callback_query(F.data == "settings_message_length", SettingsStates.main_menu)
async def cb_message_length(callback: types.CallbackQuery, state: FSMContext):
    # Check admin permissions again
    chat_id = (await state.get_data())['chat_id']
    if not await is_user_admin(chat_id, callback.from_user.id):
        await callback.answer("You need to be an admin to change chat settings.", show_alert=True)
        logger.warning(f"User {callback.from_user.id} attempted to access message length settings without admin rights")
        return
    
    logger.info(f"User {callback.from_user.id} accessing message length settings for chat {chat_id}")
    chat = await database.get_chat(chat_id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Set Minimum Length", callback_data="set_min_length")
    builder.button(text="Set Maximum Length", callback_data="set_max_length")
    builder.button(text="Back to Main Menu", callback_data="settings_back_main")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"Current message length limits:\n"
        f"• Minimum: {chat.chat_settings.min_message_length_for_analysis} characters\n"
        f"• Maximum: {chat.chat_settings.max_message_length_for_analysis} characters\n\n"
        f"Messages outside these limits will not be analyzed.",
        reply_markup=builder.as_markup()
    )

@settings_router.callback_query(F.data == "set_min_length")
async def cb_set_min_length(callback: types.CallbackQuery, state: FSMContext):
    # Check admin permissions again
    chat_id = (await state.get_data())['chat_id']
    if not await is_user_admin(chat_id, callback.from_user.id):
        await callback.answer("You need to be an admin to change chat settings.", show_alert=True)
        logger.warning(f"User {callback.from_user.id} attempted to set min length without admin rights")
        return
    
    logger.info(f"User {callback.from_user.id} setting min message length for chat {chat_id}")
    await callback.message.edit_text(
        "Enter the minimum message length for analysis (in characters):"
    )
    
    await state.set_state(SettingsStates.min_message_length)

@settings_router.message(SettingsStates.min_message_length)
async def process_min_length(message: types.Message, state: FSMContext):
    data = await state.get_data()
    chat_id = data['chat_id']
    
    # Check admin status again
    if not await is_user_admin(chat_id, message.from_user.id):
        await message.reply("You no longer have admin permissions for this chat.")
        await state.clear()
        logger.warning(f"User {message.from_user.id} lost admin rights while setting min message length")
        return
    
    try:
        min_length = int(message.text)
        if min_length >= 0:
            chat = await database.get_chat(chat_id)
            
            chat.chat_settings.min_message_length_for_analysis = min_length
            await database.update_chat(chat_id, {"chat_settings": chat.chat_settings.dict()})
            logger.info(f"Updated min message length to {min_length} for chat {chat_id}")
            
            await message.reply(f"Minimum message length updated to {min_length} characters")
            
            # Return to main menu
            builder = InlineKeyboardBuilder()
            builder.button(text="Back to Main Menu", callback_data="settings_back_main")
            await message.reply("What would you like to do next?", reply_markup=builder.as_markup())
        else:
            await message.reply("Value must be a non-negative integer. Please try again.")
            logger.warning(f"Invalid min length: {min_length} - negative value")
    except ValueError:
        await message.reply("Please enter a valid integer.")
        logger.warning(f"Invalid min length: {message.text} - not an integer")

@settings_router.callback_query(F.data == "set_max_length")
async def cb_set_max_length(callback: types.CallbackQuery, state: FSMContext):
    # Check admin permissions again
    chat_id = (await state.get_data())['chat_id']
    if not await is_user_admin(chat_id, callback.from_user.id):
        await callback.answer("You need to be an admin to change chat settings.", show_alert=True)
        logger.warning(f"User {callback.from_user.id} attempted to set max length without admin rights")
        return
    
    logger.info(f"User {callback.from_user.id} setting max message length for chat {chat_id}")
    await callback.message.edit_text(
        "Enter the maximum message length for analysis (in characters):"
    )
    
    await state.set_state(SettingsStates.max_message_length)

@settings_router.message(SettingsStates.max_message_length)
async def process_max_length(message: types.Message, state: FSMContext):
    data = await state.get_data()
    chat_id = data['chat_id']
    
    # Check admin status again
    if not await is_user_admin(chat_id, message.from_user.id):
        await message.reply("You no longer have admin permissions for this chat.")
        await state.clear()
        logger.warning(f"User {message.from_user.id} lost admin rights while setting max message length")
        return
    
    try:
        max_length = int(message.text)
        if max_length > 0:
            chat = await database.get_chat(chat_id)
            
            chat.chat_settings.max_message_length_for_analysis = max_length
            await database.update_chat(chat_id, {"chat_settings": chat.chat_settings.dict()})
            logger.info(f"Updated max message length to {max_length} for chat {chat_id}")
            
            await message.reply(f"Maximum message length updated to {max_length} characters")
            
            # Return to main menu
            builder = InlineKeyboardBuilder()
            builder.button(text="Back to Main Menu", callback_data="settings_back_main")
            await message.reply("What would you like to do next?", reply_markup=builder.as_markup())
        else:
            await message.reply("Value must be a positive integer. Please try again.")
            logger.warning(f"Invalid max length: {max_length} - not positive")
    except ValueError:
        await message.reply("Please enter a valid integer.")
        logger.warning(f"Invalid max length: {message.text} - not an integer")

# === MIN MESSAGES FOR NEW USERS HANDLERS ===
@settings_router.callback_query(F.data == "settings_min_messages", SettingsStates.main_menu)
async def cb_min_messages(callback: types.CallbackQuery, state: FSMContext):
    # Check admin permissions again
    chat_id = (await state.get_data())['chat_id']
    if not await is_user_admin(chat_id, callback.from_user.id):
        await callback.answer("You need to be an admin to change chat settings.", show_alert=True)
        logger.warning(f"User {callback.from_user.id} attempted to access min messages settings without admin rights")
        return
    
    logger.info(f"User {callback.from_user.id} accessing min messages settings for chat {chat_id}")
    await callback.message.edit_text(
        "Enter the minimum number of analyzed messages required for new members:\n\n"
        "This sets how many messages a new user must send before their language "
        "statistics are calculated."
    )
    
    await state.set_state(SettingsStates.new_members_min_messages)

@settings_router.message(SettingsStates.new_members_min_messages)
async def process_min_messages(message: types.Message, state: FSMContext):
    data = await state.get_data()
    chat_id = data['chat_id']
    
    # Check admin status again
    if not await is_user_admin(chat_id, message.from_user.id):
        await message.reply("You no longer have admin permissions for this chat.")
        await state.clear()
        logger.warning(f"User {message.from_user.id} lost admin rights while setting min messages")
        return
    
    try:
        min_messages = int(message.text)
        if min_messages >= 0:
            chat = await database.get_chat(chat_id)
            
            chat.chat_settings.new_members_min_analyzed_messages = min_messages
            await database.update_chat(chat_id, {"chat_settings": chat.chat_settings.dict()})
            logger.info(f"Updated min analyzed messages to {min_messages} for chat {chat_id}")
            
            await message.reply(f"Minimum analyzed messages for new users updated to {min_messages}")
            
            # Return to main menu
            builder = InlineKeyboardBuilder()
            builder.button(text="Back to Main Menu", callback_data="settings_back_main")
            await message.reply("What would you like to do next?", reply_markup=builder.as_markup())
        else:
            await message.reply("Value must be a non-negative integer. Please try again.")
            logger.warning(f"Invalid min messages: {min_messages} - negative value")
    except ValueError:
        await message.reply("Please enter a valid integer.")
        logger.warning(f"Invalid min messages: {message.text} - not an integer")

# Add handlers for editing and deleting existing rules
# Update the rule display function
@settings_router.callback_query(F.data.startswith("edit_rule_"), SettingsStates.moderation_rules_list)
async def cb_edit_rule(callback: types.CallbackQuery, state: FSMContext):
    # Check admin permissions again
    chat_id = (await state.get_data())['chat_id']
    if not await is_user_admin(chat_id, callback.from_user.id):
        await callback.answer("You need to be an admin to change chat settings.", show_alert=True)
        logger.warning(f"User {callback.from_user.id} attempted to edit rule without admin rights")
        return
    
    rule_index = int(callback.data.split("_")[-1])
    await state.update_data(rule_index=rule_index)
    logger.info(f"User {callback.from_user.id} editing rule {rule_index} for chat {chat_id}")
    
    chat = await database.get_chat(chat_id)
    
    if rule_index >= len(chat.chat_settings.moderation_rules):
        await callback.message.edit_text("Rule not found. Please try again.")
        logger.warning(f"Rule index {rule_index} out of bounds for chat {chat_id}")
        return
    
    rule = chat.chat_settings.moderation_rules[rule_index]
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Delete Rule", callback_data=f"delete_rule_{rule_index}")
    builder.button(text="Back to Rules List", callback_data="settings_moderation_rules")
    builder.adjust(1)
    
    conditions_text = []
    for i, cond in enumerate(rule.conditions):
        condition_desc = f"• Condition {i+1}: {format_condition_type(cond.type)}"
        conditions_text.append(condition_desc)
        
        if cond.values:
            # Format values for readability based on condition type
            if cond.type == RuleConditionType.SINGLE_MESSAGE_LANGUAGE_CONFIDENCE:
                conditions_text.append(f"  • Confidence threshold: {cond.values.get('threshold', 'N/A')}")
            
            elif cond.type == RuleConditionType.SINGLE_MESSAGE_CONFIDENCE_NOT_IN_ALLOWED_LANGUAGES:
                conditions_text.append(f"  • Confidence threshold: {cond.values.get('threshold', 'N/A')}")
            
            elif cond.type == RuleConditionType.PREVIOUS_RESTRICTION_TYPE_COUNT:
                restriction_types = cond.values.get('restriction_type', ['any'])
                if isinstance(restriction_types, str):
                    restriction_types = [restriction_types]  # Convert to list for backward compatibility
                    
                types_display = ", ".join(restriction_types) if restriction_types != ["any"] else "any"
                conditions_text.append(f"  • Restriction types: {types_display}")
                conditions_text.append(f"  • Count: {cond.values.get('count', 'N/A')}")
            
            elif cond.type == RuleConditionType.PREVIOUS_RESTRICTION_TYPE_TIME_LENGTH:
                restriction_types = cond.values.get('restriction_type', ['any'])
                if isinstance(restriction_types, str):
                    restriction_types = [restriction_types]  # Convert to list for backward compatibility
                    
                types_display = ", ".join(restriction_types) if restriction_types != ["any"] else "any"
                conditions_text.append(f"  • Restriction types: {types_display}")
                conditions_text.append(f"  • Cumulative duration: {cond.values.get('seconds', 'N/A')} seconds")
                conditions_text.append(f"  • Within time window: {cond.values.get('window_hours', 'N/A')} hours")
            
            else:
                # Generic fallback for unknown condition types
                for key, val in cond.values.items():
                    conditions_text.append(f"  • {key}: {val}")
    
    restriction_details = [
        f"Type: {rule.restriction.restriction_type}",
    ]

    if rule.restriction.restriction_justification_message:
        restriction_details.append(f"Justification: {rule.restriction.restriction_justification_message}")

    if rule.restriction.duration_seconds:
        restriction_details.append(f"Duration: {rule.restriction.duration_seconds} seconds")
    
    rule_name_display = f"Name: {rule.name}\n\n" if hasattr(rule, 'name') and rule.name else ""

    await callback.message.edit_text(
        f"Rule {rule_index+1}:\n\n"
        f"{rule_name_display}"
        f"Message: {rule.message}\n\n"
        f"Restriction:\n" + "\n".join(restriction_details) + "\n\n"
        f"Notify user: {'Yes' if rule.notify_user else 'No'}\n\n"
        f"Conditions ({rule.condition_relation}):\n" + "\n".join(conditions_text),
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(SettingsStates.edit_rule)

# Helper function to format condition type names nicely
def format_condition_type(condition_type: str) -> str:
    """Format a condition type to be more readable"""
    if isinstance(condition_type, RuleConditionType):
        condition_type = condition_type.value
        
    return condition_type.replace('_', ' ').title()

@settings_router.callback_query(F.data.startswith("delete_rule_"), SettingsStates.edit_rule)
async def cb_delete_rule(callback: types.CallbackQuery, state: FSMContext):
    # Check admin permissions again
    chat_id = (await state.get_data())['chat_id']
    if not await is_user_admin(chat_id, callback.from_user.id):
        await callback.answer("You need to be an admin to change chat settings.", show_alert=True)
        logger.warning(f"User {callback.from_user.id} attempted to delete rule without admin rights")
        return
    
    rule_index = int(callback.data.split("_")[-1])
    logger.info(f"User {callback.from_user.id} deleting rule {rule_index} for chat {chat_id}")
    
    chat = await database.get_chat(chat_id)
    
    if rule_index < len(chat.chat_settings.moderation_rules):
        chat.chat_settings.moderation_rules.pop(rule_index)
        await database.update_chat(chat_id, {"chat_settings": chat.chat_settings.dict()})
        logger.info(f"Deleted rule {rule_index} from chat {chat_id}")
        
        await callback.message.edit_text("Rule deleted successfully!")
    else:
        await callback.message.edit_text("Rule not found.")
        logger.warning(f"Rule index {rule_index} out of bounds for chat {chat_id}")
    
    # Return to moderation rules list
    await cb_moderation_rules(callback, state)
    
# === GENERAL NAVIGATION HANDLERS ===
@settings_router.callback_query(F.data == "settings_back_main")
async def cb_back_to_main(callback: types.CallbackQuery, state: FSMContext):
    # Check admin permissions again
    chat_id = (await state.get_data())['chat_id']
    if not await is_user_admin(chat_id, callback.from_user.id):
        await callback.answer("You need to be an admin to change chat settings.", show_alert=True)
        logger.warning(f"User {callback.from_user.id} attempted to navigate without admin rights")
        return
    
    logger.info(f"User {callback.from_user.id} returning to main menu for chat {chat_id}")
    chat = await database.get_chat(chat_id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Allowed Languages", callback_data="settings_allowed_languages")
    builder.button(text="Analysis Frequency", callback_data="settings_analysis_frequency")
    builder.button(text="Message Length Limits", callback_data="settings_message_length")
    builder.button(text="Minimum Messages for New Users", callback_data="settings_min_messages")
    builder.button(text="Moderation Rules", callback_data="settings_moderation_rules")
    builder.button(text="Close", callback_data="settings_close")
    builder.adjust(1)  # One button per row
    
    await callback.message.edit_text(
        f"Chat Settings for {chat.last_known_name}\n\n"
        f"Current settings:\n"
        f"• Allowed languages: {', '.join(chat.chat_settings.allowed_languages)}\n"
        f"• Analysis frequency: {chat.chat_settings.analysis_frequency}\n"
        f"• Min message length: {chat.chat_settings.min_message_length_for_analysis}\n"
        f"• Max message length: {chat.chat_settings.max_message_length_for_analysis}\n"
        f"• New members min messages: {chat.chat_settings.new_members_min_analyzed_messages}\n"
        f"• Moderation rules: {len(chat.chat_settings.moderation_rules)}\n\n"
        f"Select a setting to modify:",
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(SettingsStates.main_menu)

@settings_router.callback_query(F.data == "settings_close")
async def cb_close_settings(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"User {callback.from_user.id} closing settings dialog")
    await callback.message.edit_text("Settings closed. Thank you for configuring your chat!")
    await state.clear()