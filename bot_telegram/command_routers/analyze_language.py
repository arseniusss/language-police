from aiogram import Router, types
from aiogram.filters import Command
from langdetect import detect_langs
from backend.functions.helpers.get_lang_display import get_language_display

analyze_language_router = Router()

@analyze_language_router.message(Command("analyze_language"))
async def cmd_analyze_language(message: types.Message):
    """Manually analyze language of a message using langdetect"""
    
    text_to_analyze = None
    
    # Check if replying to a message
    if message.reply_to_message and message.reply_to_message.text:
        text_to_analyze = message.reply_to_message.text
    else:
        # Check if text is provided as argument
        command_args = message.text.split(' ', 1)
        if len(command_args) > 1:
            text_to_analyze = command_args[1]
    
    if not text_to_analyze:
        await message.reply(
            "❌ Please either:\n"
            "• Reply to a message with `/analyze_language`\n"
            "• Use `/analyze_language <text>` to analyze specific text"
        )
        return
    
    if len(text_to_analyze.strip()) < 3:
        await message.reply("❌ Text is too short for reliable language detection (minimum 3 characters)")
        return
    
    try:
        # Detect languages with confidence scores
        detected_languages = detect_langs(text_to_analyze)
        
        if not detected_languages:
            await message.reply("❌ Could not detect any language in the provided text")
            return
        
        # Prepare the response
        truncated_text = text_to_analyze[:100] + "..." if len(text_to_analyze) > 100 else text_to_analyze
        
        response_text = f"🔍 **Language Analysis**\n\n"
        response_text += f"📝 **Text:** `{truncated_text}`\n\n"
        response_text += "🌐 **Detected Languages:**\n"
        
        # Sort by confidence (highest first)
        sorted_languages = sorted(detected_languages, key=lambda x: x.prob, reverse=True)
        
        # Build the detailed response
        for i, lang in enumerate(sorted_languages):
            confidence_percent = round(lang.prob * 100, 1)
            
            # Get emoji and name for this language
            lang_display = get_language_display(lang.lang)
            
            if i == 0:  # Most likely language
                response_text += f"🥇 **{lang_display}** - {confidence_percent}%\n"
            else:
                response_text += f"• {lang_display} - {confidence_percent}%\n"
        
        await message.reply(response_text, parse_mode="Markdown")
        
    except Exception as e:
        await message.reply(f"❌ Language detection failed: {str(e)}")
    except Exception as e:
        await message.reply(f"❌ An error occurred during analysis: {str(e)}")