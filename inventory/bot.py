import asyncio
from pathlib import Path
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    Application,
    MessageHandler,
    ContextTypes,
    BaseHandler,
    PicklePersistence,
    CommandHandler,
)
from inventory import orm
from loguru import logger
from inventory.container import (
    Container,
    Provide,
    inject,
    PostgresqlDatabase,
    NotionClient,
    S3FileSystem,
)
from uuid import uuid4

from inventory.enums import ItemType


class WhitelistHandler(BaseHandler):
    def __init__(self, **kwargs):
        kwargs["callback"] = self.callback_fn
        super().__init__(**kwargs)

    def check_update(self, update: Update) -> bool:
        tg_user = update.effective_user
        if tg_user is None:
            # Telegram update without user (e.g. poll update)
            return True
        if orm.User.get_or_none(telegram_id=tg_user.id) is None:
            logger.warning(f"Unauthorized access: {tg_user.full_name} ({tg_user.id})")
            return True
        return False

    async def callback_fn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message is not None:
            await update.message.reply_text("Permission denied")


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is not None:
        user = orm.User.get(telegram_id=update.effective_user.id)
        await update.message.reply_text(f"Hello, {user.name}")


async def upload_image(
    s3_image_path: Path,
    tg_file: ...,
    s3fs: S3FileSystem = Provide[Container.s3fs],
):
    try:
        with s3fs.open(s3_image_path, "wb") as s3_file:
            await tg_file.download_to_memory(s3_file)
    except:
        logger.exception("Image upload failed")


@inject
async def add_item(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    s3_public_url: str = Provide[Container.settings.s3_public_url],
    database: PostgresqlDatabase = Provide[Container.database],
):
    # Спарсить текст и картинку (* не разобрали случай без картинки)
    # Залить картинку
    # Сгенерировать ID из БД
    # Создать страничку
    # Коммитнуть в БД
    # Отправить сообщение с ID и ссылкой на страничку

    if not update.message.photo:
        await update.message.reply_text("Photo required")
        return

    with database.transaction():
        item_name = update.message.caption[:200]  # TODO: Check length
        item = orm.InventoryItem(name=item_name, type=ItemType.OBJECT)
        item.save()
        msg = await update.message.reply_text(f"⌛ Item ID: {item.id}: uploading...")

        image = update.message.photo[-1]
        tg_file = await context.bot.get_file(image.file_id)
        ext = tg_file.file_path.split(".")[-1]
        s3_image_path = Path(f"<bucket>/images/{uuid4()}.{ext}")
        s3_image_url = s3_public_url + f"images/{s3_image_path.name}"
        await upload_image(s3_image_path, tg_file)

        notion_url = await create_notion_page(f"{item.id:05d}", item_name, s3_image_url)
        await msg.edit_text(f"✅ Item ID: {item.id}: {notion_url}")



@inject
async def create_notion_page(
    item_id: str,
    item_name: str,
    image_url: str,
    notion: NotionClient = Provide[Container.notion],
    notion_database_id: str = Provide[Container.settings.notion_database_id],
):
    response = await notion.pages.create(
        parent={"database_id": notion_database_id},
        properties={
            "ID": {"rich_text": [{"text": {"content": item_id}}]},
            "Name": {"title": [{"text": {"content": item_name}}]},
        },
        children=[
            {
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {"url": image_url},
                },
            }
        ],
    )
    return response.get("url")


@inject
def init_bot(
    telegram_token: str = Provide[Container.settings.telegram_token],
) -> Application:
    # TODO: Persistence (bonus task: store in postgres)
    # persistence = PicklePersistence(filepath=data_path / "bot_state.pkl")
    app = ApplicationBuilder().token(telegram_token).build()
    app.add_handler(WhitelistHandler())
    app.add_handler(CommandHandler(["start", "help"], hello))
    app.add_handler(MessageHandler(None, add_item))
    return app
