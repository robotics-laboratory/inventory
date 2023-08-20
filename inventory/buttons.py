import inspect
import json
from typing import Callable

from pydantic import BaseModel
from telegram import InlineKeyboardButton


class ButtonData(BaseModel):
    """
    Model for inline buttons' callback data
    """

    frame: str
    action: str
    extra: dict

    # TODO: Try again to switch to pydantic 2.x
    def encode(self) -> str:
        data = {"f": self.frame, "a": self.action, "e": self.extra}
        data = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        assert len(data) <= 64
        return data

    @classmethod
    def decode(cls, data: str) -> "ButtonData":
        data = json.loads(data)
        return cls(frame=data["f"], action=data["a"], extra=data["e"])


class ActionButton(InlineKeyboardButton):
    def __init__(self, text: str, action: Callable, **kwargs):
        assert inspect.ismethod(action)
        klass = action.__self__.__class__
        assert getattr(klass, "frame_id", None) is not None
        data = ButtonData(frame=klass.frame_id, action=action.__name__, extra=kwargs)
        super().__init__(text, callback_data=data.encode())


class TransitionButton(InlineKeyboardButton):
    def __init__(self, text: str, frame_class: type, **kwargs):
        assert getattr(frame_class, "frame_id", None) is not None
        data = ButtonData(frame=frame_class.frame_id, action="render", extra=kwargs)
        super().__init__(text, callback_data=data.encode())
