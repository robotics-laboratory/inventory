from typing import ClassVar, Optional, Sequence, Type

from telegram import InlineKeyboardMarkup
from telegram.ext import ContextTypes

from inventory import orm
from inventory.buttons import ActionButton, TransitionButton


class BaseFrame:
    """
    Base class for long-living interactive messages (aka forms)
    """

    # Unique frame ID. Required for all non-meta subclasses
    frame_id: ClassVar[str] = None

    # Internal subclasses registry mapping: frame id -> frame class
    # TODO: type hint: ClassVar[Dict[str, Type["BaseFrame"]]]
    __registry: ... = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.frame_id is not None:
            if cls.frame_id in cls.__registry:
                raise RuntimeError(f"Duplicate frame id: {cls.frame_id} ({cls})")
            cls.__registry[cls.frame_id] = cls

    @classmethod
    def get_frame_class(cls, frame_id: str) -> Optional[Type["BaseFrame"]]:
        return cls.__registry.get(frame_id)

    def __init__(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        message_id: int,
        callback_data: dict,
    ):
        self.context = context
        self.message_id = message_id
        self.callback_data = callback_data

    async def prepare(self):
        """
        Always called after initializing the frame. Default implementation does nothing.
        """
        pass

    async def render(self):
        """
        Main method for rendering, i.e. updating existing message with new data
        """
        text = await self.render_text()
        keyboard = [
            x if isinstance(x, Sequence) else [x] async for x in self.render_buttons()
        ]
        await self.context.bot.edit_message_text(
            text=text,
            chat_id=self.context._chat_id,
            message_id=self.message_id,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    async def render_text(self):
        """
        Render method for message text. Implement in subclasses.
        """
        raise NotImplementedError

    async def render_buttons(self):
        """
        Render method for inline buttons. Implement in subclasses.
        """
        raise NotImplementedError


class BrokenFrameError(RuntimeError):
    """
    Tells the dispatcher that frame is no longer valid or is critically broken
    """

    pass


class BaseItemFrame(BaseFrame):
    """
    Base frame for all item-related stuff
    """

    async def prepare(self):
        self.item_id = self.callback_data["item_id"]
        self.item = orm.InventoryItem.get_or_none(self.item_id)
        if self.item is None:
            raise BrokenFrameError(
                f"🚫 Item <code>{self.item_id}</code> no longer exists"
            )

    def extra(self):
        return {"item_id": self.item_id}

    async def render_text(self):
        lines = []
        page_url = f"https://notion.so/{str(self.item.page_id).replace('-', '')}"
        lines.append(
            f"📦 <code>{self.item.id}</code> • "
            f'<a href="{page_url}">{self.item.name}</a>'
        )
        lines.append(f"Quantity: {self.item.quantity}")
        return "\n".join(lines)


class MainFrame(BaseItemFrame):
    frame_id = "main"

    async def render_buttons(self):
        yield ActionButton("Test button", self.test, **self.extra())
        yield TransitionButton("Edit quantity", TestSubMenu, **self.extra())

    async def test(self):
        chat_id = self.context._chat_id
        await self.context.bot.send_message(
            chat_id=chat_id,
            text=f"Test method called from item {self.item.id}",
        )


class TestSubMenu(BaseItemFrame):
    frame_id = "qty"

    async def render_text(self):
        text = await super().render_text()
        text += "\nEdit item quantity:"
        return text

    async def render_buttons(self):
        yield [
            ActionButton("➖ Decrease", self.update_quantity, inc=-1, **self.extra()),
            ActionButton("➕ Increase", self.update_quantity, inc=+1, **self.extra()),
        ]
        yield TransitionButton("« Back to main menu", MainFrame, **self.extra())

    async def update_quantity(self):
        delta = self.callback_data["inc"]
        self.item.quantity += delta
        self.item.save()
        await self.render()
