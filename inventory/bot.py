from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import List, cast
from uuid import uuid4

from loguru import logger
from telegram import InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    Defaults,
    MessageHandler,
)

from inventory import orm
from inventory.buttons import ButtonData
from inventory.container import (
    Container,
    PostgresqlDatabase,
    Provide,
    S3FileSystem,
    inject,
)
from inventory.enums import ItemType
from inventory.frames import BaseFrame, BrokenFrameError, MainFrame
from inventory.notion import PAGE_TEMPLATES, create_page_nested


@dataclass
class MessageDict:
    photo_id: str
    caption: str


def whitelist_restricted(func):
    @wraps(func)
    async def wrapped(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        tg_user = update.effective_user

        if orm.User.get_or_none(telegram_id=tg_user.id) is None:
            logger.warning(
                "Unauthorized access:\n",
                f"{tg_user.full_name} ({tg_user.id}) [{tg_user.username}]",
            )
            if update.message is not None:
                await update.message.reply_text("Permission denied")
            return
        return await func(update, context, *args, **kwargs)

    return wrapped


# class WhitelistHandler(BaseHandler):
#     def __init__(self, **kwargs):
#         kwargs["callback"] = self.callback_fn
#         super().__init__(**kwargs)

#     def check_update(self, update: Update) -> bool:
#         tg_user = update.effective_user
#         if tg_user is None:
#             # Telegram update without user (e.g. poll update)
#             return True
#         if orm.User.get_or_none(telegram_id=tg_user.id) is None:
#             logger.warning(f"Unauthorized access: {tg_user.full_name} ({tg_user.id})")
#             return True
#         return False

#     async def callback_fn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         if update.message is not None:
#             await update.message.reply_text("Permission denied")


@whitelist_restricted
async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is not None:
        user = orm.User.get(telegram_id=update.effective_user.id)
        await update.message.reply_text(f"Hello, {user.full_name}")


# TODO: Maybe merge with upload_tg_image?
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


async def upload_tg_image(
    context,
    tg_image_id: str,
    s3_public_url: str = Provide[Container.settings.s3_public_url],
    s3_bucket: str = Provide[Container.settings.s3_bucket],
):
    photo = await context.bot.get_file(tg_image_id)
    ext = photo.file_path.split(".")[-1]
    s3_image_path = Path(f"{s3_bucket}/images/{uuid4()}.{ext}")
    s3_image_url = s3_public_url + f"images/{s3_image_path.name}"
    await upload_image(s3_image_path, photo)
    return s3_image_url


async def add_item(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    name: str,
    tg_image_ids: List[str],
    database: PostgresqlDatabase = Provide[Container.database],
    notion_database_id: str = Provide[Container.settings.notion_database_id],
):
    with database.transaction():
        # Prepare item model
        name, type = parse_name(name)
        # TODO: Select type properly
        item = orm.InventoryItem(name=name, type=ItemType.OBJECT)
        item.save()
        # Send message
        msg = f"⌛ Item ID: {item.id}: uploading...\n(using template: {type})"
        msg = await context.bot.send_message(chat_id, text=msg)
        # Upload images to S3 and get urls
        image_urls = [await upload_tg_image(context, id) for id in tg_image_ids]
        # Render page template
        template_class = PAGE_TEMPLATES.get(type, PAGE_TEMPLATES["default"])
        blocks = await template_class().render({"images": image_urls})
        response = await create_page_nested(
            parent={"database_id": notion_database_id},
            properties={
                "ID": {"rich_text": [{"text": {"content": f"{item.id:05d}"}}]},
                "Name": {"title": [{"text": {"content": name}}]},
            },
            children=blocks,
        )
        notion_url = response["url"]
        item.page_id = response["id"]
        item.save()
        # Update message
        frame = MainFrame(context, msg.message_id, {"item_id": item.id})
        await frame.prepare()
        await frame.render()
        logger.info(f"Item added - id: {item.id}, url: {notion_url}")


def parse_name(name: str):
    # If message starts with "type:xxx", return "xxx" as item type
    type = "default"
    prefix, *remainder = name.split()
    if prefix.startswith("type:"):
        type = prefix.split(":")[1]
        name = " ".join(remainder)
    return name, type


@inject
async def media_group_publisher(context: CallbackContext):
    job_data = cast(List[MessageDict], context.job.data)
    item_name = job_data[0].caption  # TODO: Check length
    image_ids = [x.photo_id for x in job_data]
    await add_item(context, context._chat_id, item_name, image_ids)


@whitelist_restricted
async def add_item_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.media_group_id is not None:
        # Multiple images
        photo_id = update.message.photo[-1].file_id
        caption = update.message.caption
        msg_dict = MessageDict(photo_id, caption)
        jobs = context.job_queue.get_jobs_by_name(str(update.message.media_group_id))
        assert len(jobs) <= 1
        if jobs:
            jobs[0].data.append(msg_dict)
        else:
            context.job_queue.run_once(
                callback=media_group_publisher,
                when=2,  # FIXME
                data=[msg_dict],
                chat_id=update.effective_message.chat_id,
                name=str(update.message.media_group_id),
            )
        return

    if update.message.photo:
        # One image
        item_name = update.message.caption
        image_ids = [update.message.photo[-1].file_id]
    else:
        # No images
        item_name = update.message.text
        image_ids = []
    await add_item(context, update.effective_message.chat_id, item_name, image_ids)


# TODO: Переделать на класс, почистить
async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    async def teardown(message: str):
        # Вызываем в случае критической ошибки
        await query.message.edit_text(message, reply_markup=InlineKeyboardMarkup([]))
        await query.answer()

    data = ButtonData.decode(query.data)
    frame_class = BaseFrame.get_frame_class(data.frame)
    if frame_class is None:
        return await teardown(f"Unknown frame id: {data.frame}")

    try:
        frame = frame_class(context, query.message.message_id, data.extra)
        await frame.prepare()
        method = getattr(frame, data.action, None)
        if method is None:
            return await teardown(f"Unknown action: {data.action}")
        await method()
    except BrokenFrameError as e:
        return await teardown(str(e))
    await query.answer()


@whitelist_restricted
async def get_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        return await update.message.reply_text("Usage: /get [item id]")
    item_id = context.args[0]
    if not item_id.isnumeric():
        return await update.message.reply_text("Incorrect item id")
    item = orm.InventoryItem.get_or_none(int(item_id))
    if item is None:
        return await update.message.reply_text("Item not found")
    msg = await update.message.reply_text("Please wait...")
    frame = MainFrame(context, msg.message_id, {"item_id": item.id})
    await frame.prepare()
    await frame.render()


@inject
def init_bot(
    telegram_token: str = Provide[Container.settings.telegram_token],
) -> Application:
    # TODO: Persistence (bonus task: store in postgres)
    # persistence = PicklePersistence(filepath=data_path / "bot_state.pkl")
    defaults = Defaults(parse_mode=ParseMode.HTML)
    app = ApplicationBuilder().token(telegram_token).defaults(defaults).build()
    # app.add_handler(WhitelistHandler())
    app.add_handler(CommandHandler(["start", "help"], hello))
    app.add_handler(CommandHandler("get", get_item))
    app.add_handler(MessageHandler(None, add_item_cmd))
    app.add_handler(CallbackQueryHandler(button_router))
    return app
