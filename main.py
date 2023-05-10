import asyncio

import nest_asyncio
from loguru import logger

from inventory import orm
from inventory.bot import init_bot
from inventory.container import Container, Settings


async def main():
    container = Container()
    container.settings.from_pydantic(Settings())
    print(Settings())
    return
    container.wire(packages=["inventory"])
    container.init_resources()

    # ORM usage demo
    total_users = orm.User.select().count()
    logger.info(f"Total users in DB: {total_users}")

    bot = init_bot()
    nest_asyncio.apply()
    bot.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
