import asyncio
from bot import dp, bot
from middlewares.database.db import database
import logging
import sys


async def main():
    
    await database.setup()
    dp.update.middleware.register(database)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())