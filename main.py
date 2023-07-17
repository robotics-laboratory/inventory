import asyncio

import nest_asyncio

from inventory.bot import init_bot
from inventory.container import Container, Settings


async def main():
    container = Container()
    container.settings.from_pydantic(Settings())
    container.wire(packages=["inventory"])
    container.init_resources()

    bot = init_bot()
    nest_asyncio.apply()
    bot.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
