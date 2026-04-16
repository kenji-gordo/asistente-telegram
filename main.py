#!/usr/bin/env python3
"""Main entry point for the Telegram bot"""

import asyncio
import logging
from telegram import Bot
from telegram.ext import Application
from aiohttp import web
from bot.telegram_bot import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def health(request):
    """Health check endpoint"""
    return web.Response(text="OK")


async def run_bot():
    """Run the Telegram bot"""
    logger.info("Starting Telegram bot...")

    app = create_app()

    logger.info("Bot is running.")
    await app.initialize()
    await app.start()

    # Start polling
    polling_task = asyncio.create_task(
        app.updater.start_polling(drop_pending_updates=True, allowed_updates=["message", "voice"])
    )

    # Wait a bit to see if polling starts correctly
    await asyncio.sleep(2)

    if polling_task.done() and not polling_task.cancelled():
        exception = polling_task.exception()
        if exception:
            logger.error(f"Polling failed: {exception}")
        else:
            logger.info("Polling task completed normally")

    # Keep running
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        await app.stop()


async def main():
    """Start the bot with web server for health checks"""
    # Create a simple web server for health checks on port 8000
    app = web.Application()
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()

    logger.info("Health check server started on port 8000")

    # Run the bot
    await run_bot()


if __name__ == "__main__":
    asyncio.run(main())