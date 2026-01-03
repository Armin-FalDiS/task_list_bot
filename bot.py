"""
Telegram Task List Bot
A simple bot that manages a shared task list for groups.
"""

import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from database import close_connection_pool
from utils import generate_webhook_secret
from handlers import (
    start, show_list, show_text_list, add_task, remove_task_command,
    assign_task, set_task_details, append_task_details, show_my_tasks,
    set_task_deadline, handle_text, handle_callback_query
)

load_dotenv()

log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, log_level, logging.INFO)
)
logger = logging.getLogger(__name__)

async def main():
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        return
    
    application = Application.builder().token(bot_token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", show_list))
    application.add_handler(CommandHandler("text", show_text_list))
    application.add_handler(CommandHandler("mytasks", show_my_tasks))
    application.add_handler(CommandHandler("add", add_task))
    application.add_handler(CommandHandler("remove", remove_task_command))
    application.add_handler(CommandHandler("assign", assign_task))
    application.add_handler(CommandHandler("details", set_task_details))
    application.add_handler(CommandHandler("deadline", set_task_deadline))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/details\+"), set_task_details))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    webhook_url = os.getenv('WEBHOOK_URL')
    webhook_path = os.getenv('WEBHOOK_PATH', '/task-bot')
    
    if webhook_url:
        try:
            logger.info(f"🌐 Starting bot with webhook mode...")
            logger.info(f"📡 Webhook URL: {webhook_url}")
            logger.info(f"🔌 Port: 8443")
            logger.info(f"🛤️ Path: {webhook_path}")
            
            webhook_secret = generate_webhook_secret()
            logger.info(f"🔐 Generated webhook secret token: {webhook_secret}")
            logger.info("⚠️  IMPORTANT: Configure nginx with this secret token in the X-Telegram-Bot-Api-Secret-Token header")
            
            full_webhook_url = f"{webhook_url.rstrip('/')}{webhook_path}"
            logger.info(f"🔗 Full webhook URL: {full_webhook_url}")
            
            await application.initialize()
            await application.start()
            await application.updater.start_webhook(
                listen="0.0.0.0",
                port=8443,
                webhook_url=full_webhook_url,
                url_path=webhook_path,
                secret_token=webhook_secret
            )
            logger.info("🌐 Webhook started successfully")
            
            try:
                await asyncio.Event().wait()
            except KeyboardInterrupt:
                logger.info("🛑 Shutting down bot...")
            finally:
                await application.updater.stop()
                await application.stop()
                await application.shutdown()
                close_connection_pool()
                
        except Exception as e:
            logger.error(f"❌ Error starting webhook mode: {e}")
            logger.info("🔄 Falling back to polling mode...")
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
            logger.info("🔄 Polling started successfully")
            
            try:
                await asyncio.Event().wait()
            except KeyboardInterrupt:
                logger.info("🛑 Shutting down bot...")
        finally:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            close_connection_pool()
    else:
        logger.info("🔄 Starting bot with polling mode...")
        logger.info("ℹ️ WEBHOOK_URL not set - using polling")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        logger.info("🔄 Polling started successfully")
        
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down bot...")
        finally:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            close_connection_pool()

if __name__ == '__main__':
    asyncio.run(main())
