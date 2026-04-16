import logging
import tempfile
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from services.extractor import extractor
from services.transcriber import transcriber
from services.calendar_service import calendar_service

logger = logging.getLogger(__name__)

# Help text in Spanish
HELP_TEXT = """¡Hola! Soy tu asistente de calendario.

Envíame un mensaje o nota de voz y crearé el evento en tu Google Calendar.

Categorías reconocidas:
• Universidad: AS, MAT, FIS, SSL, SO/SAO, PARA
• Trabajo
• Personal

No necesito confirmación - ¡crearé el evento directamente!"""


def format_event_response(event) -> str:
    """Format event creation response in Spanish"""
    category_emoji = {
        "universidad": "📚",
        "trabajo": "💼",
        "personal": "🏠",
        "general": "📅",
    }

    emoji = category_emoji.get(event.category, "📅")
    course_info = f" ({event.course})" if event.course else ""
    date_str = event.start_time.strftime("%d/%m/%Y")
    time_str = event.start_time.strftime("%H:%M")

    response = f"""✅ Evento creado {emoji}

📌 {event.title}
📅 {date_str} a las {time_str}
🏷️ {event.category.upper()}{course_info}
"""

    if event.description:
        response += f"\n📝 {event.description}"

    return response


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    logger.info(f"Received /start from {update.effective_user.id}")
    await update.message.reply_text(HELP_TEXT)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    await update.message.reply_text(HELP_TEXT)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    logger.info(f"Received message: {update.message.text[:50]}")

    try:
        text = update.message.text.strip()

        # Extract and create event (async calls)
        event = await extractor.extract_event(text)
        await calendar_service.create_event(event)

        response = format_event_response(event)
        await update.message.reply_text(response)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        await update.message.reply_text(
            "No pude identificar el tipo de tarea. ¿Es para la universidad, trabajo o algo personal?"
        )
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await update.message.reply_text(
            f"Ocurrió un error al procesar tu mensaje: {e}\n\nIntenta de nuevo."
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages"""
    logger.info(f"Received voice message")

    try:
        # Download voice file
        voice = update.message.voice
        voice_file = await voice.get_file()

        # Create temp file
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            await voice_file.download_to_memory(f)
            temp_path = f.name

        # Transcribe
        await update.message.reply_text("🎙️ Transcribiendo audio...")
        text = await transcriber.transcribe_audio(temp_path)

        if not text:
            await update.message.reply_text("No pude entender el audio. ¿Podrías escribirlo?")
            return

        # Extract and create event (async calls)
        event = await extractor.extract_event(text)
        await calendar_service.create_event(event)

        response = format_event_response(event)
        await update.message.reply_text(response)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        await update.message.reply_text(
            "No pude identificar el tipo de tarea. ¿Es para la universidad, trabajo o algo personal?"
        )
    except Exception as e:
        logger.error(f"Error processing voice: {e}")
        await update.message.reply_text(
            f"Ocurrió un error al procesar el audio: {e}\n\nIntenta de nuevo."
        )


def create_app() -> Application:
    """Create and configure the Telegram application"""
    from config.settings import settings

    if not settings.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not configured")

    logger.info(f"Creating app with token: {settings.TELEGRAM_BOT_TOKEN[:15]}...")

    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Add handlers - use explicit filter types for python-telegram-bot v21
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Text messages (excluding commands)
    text_filter = filters.TEXT & ~filters.COMMAND
    app.add_handler(MessageHandler(text_filter, handle_message))

    logger.info("Handlers registered successfully")
    logger.info(f"Total handlers: {len(app.handlers[0])}")

    # Add error handler
    async def error_handler(update, context):
        logger.error(f"Error handler: {context.error}")

    app.add_error_handler(error_handler)

    return app