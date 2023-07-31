from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import List, cast
from uuid import uuid4

from loguru import logger
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    BaseHandler,
    CallbackContext,
    CommandHandler,
    ContextTypes,
    MessageHandler,
)

from inventory import orm
from inventory.container import (
    Container,
    NotionClient,
    PostgresqlDatabase,
    Provide,
    S3FileSystem,
    inject,
)
from inventory.enums import ItemType


@dataclass
class MessageDict:
    photo_id: str
    caption: str
    post_id: int


def whitelist_restricted(func):
    @wraps(func)
    async def wrapped(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        tg_user = update.effective_user

        if orm.User.get_or_none(telegram_id=tg_user.id) is None:
            logger.warning(f"Unauthorized access: {tg_user.full_name} ({tg_user.id}) [{tg_user.username}]")
            if update.message is not None:
                await update.message.reply_text("Permission denied")
            return
        return await func(update, context, *args, **kwargs)

    return wrapped


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


@whitelist_restricted
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
    except Exception:
        logger.exception("Image upload failed")


# can i use update here? same for context
@inject
async def media_group_publisher(
    context: CallbackContext,
    s3_public_url: str = Provide[Container.settings.s3_public_url],
    s3_bucket: str = Provide[Container.settings.s3_bucket],
    database: PostgresqlDatabase = Provide[Container.database],
):
    with database.transaction():
        context.job.data = cast(List[MessageDict], context.job.data)
        urls = []
        item_name = context.job.data[0].caption[:200]  # TODO: Check length
        item = orm.InventoryItem(name=item_name, type=ItemType.OBJECT)
        item.save()
        msg = await context.bot.send_message(
            context._chat_id, f"⌛ Item ID: {item.id}: uploading..."
        )
        # msg = await update.message.reply_text(f"⌛ Item ID: {item.id}: uploading...")
        for msg_dict in context.job.data:
            photo = await context.bot.get_file(msg_dict.photo_id)
            ext = photo.file_path.split(".")[-1]
            s3_image_path = Path(f"{s3_bucket}/images/{uuid4()}.{ext}")
            s3_image_url = s3_public_url + f"images/{s3_image_path.name}"
            urls.append(s3_image_url)
            await upload_image(s3_image_path, photo)

        notion_url = await create_notion_page(f"{item.id:05d}", item_name, urls)
        await msg.edit_text(f"✅ Item ID: {item.id}: {notion_url}")


@whitelist_restricted
@inject
async def add_item(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    s3_public_url: str = Provide[Container.settings.s3_public_url],
    s3_bucket: str = Provide[Container.settings.s3_bucket],
    database: PostgresqlDatabase = Provide[Container.database],
):
    # Спарсить текст и картинку (* не разобрали случай без картинки)
    # TODO: случай без картинки

    if not update.message.photo:
        await update.message.reply_text("Photo required")
        return

    if update.message.media_group_id is not None:
        photo_id = update.message.photo[-1].file_id
        caption = update.message.caption
        post_id = update.message.message_id
        msg_dict = MessageDict(photo_id, caption, post_id)
        jobs = context.job_queue.get_jobs_by_name(str(update.message.media_group_id))
        if jobs:
            jobs[0].data.append(msg_dict)
        else:
            context.job_queue.run_once(
                callback=media_group_publisher,
                when=2,
                data=[msg_dict],
                chat_id=update.effective_message.chat_id,
                name=str(update.message.media_group_id),
            )
        return
    with database.transaction():
        item_name = update.message.caption[:200]  # TODO: Check length
        item = orm.InventoryItem(name=item_name, type=ItemType.OBJECT)
        item.save()
        msg = await update.message.reply_text(f"⌛ Item ID: {item.id}: uploading...")

        image = update.message.photo[-1]
        tg_file = await context.bot.get_file(image.file_id)
        ext = tg_file.file_path.split(".")[-1]
        s3_image_path = Path(f"{s3_bucket}/images/{uuid4()}.{ext}")
        s3_image_url = s3_public_url + f"images/{s3_image_path.name}"
        await upload_image(s3_image_path, tg_file)

        notion_url = await create_notion_page(
            f"{item.id:05d}", item_name, [s3_image_url]
        )
        await msg.edit_text(f"✅ Item ID: {item.id}: {notion_url}")
        return


@inject
async def create_notion_page(
    item_id: str,
    item_name: str,
    image_url: List[str],
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
                "image": {"type": "external", "external": {"url": url}},
            }
            for url in image_url
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
    # app.add_handler(WhitelistHandler())
    app.add_handler(CommandHandler(["start", "help"], hello))
    app.add_handler(MessageHandler(None, add_item))
    return app
