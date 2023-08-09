import asyncio

import nest_asyncio

from inventory.bot import init_bot
from inventory.container import Container, Settings


async def main():
    container = Container()
    container.settings.from_pydantic(Settings())
    container.init_resources()
    container.wire(packages=["inventory"])

    # TODO: Add to container
    bot = init_bot()
    nest_asyncio.apply()
    bot.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
