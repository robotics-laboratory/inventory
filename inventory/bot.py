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
from inventory.container import Container, Provide, inject


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


@inject
def init_bot(
    telegram_token: str = Provide[Container.settings.telegram_token],
) -> Application:
    # TODO: Persistence (bonus task: store in postgres)
    # persistence = PicklePersistence(filepath=data_path / "bot_state.pkl")
    app = ApplicationBuilder().token(telegram_token).build()
    app.add_handler(WhitelistHandler())
    app.add_handler(CommandHandler(["start", "help"], hello))
    return app
