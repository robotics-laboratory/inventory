from aenum import IntEnum


class ItemType(IntEnum):
    OBJECT = 0
    COLLECTION = 1

    @classmethod
    def choices(cls):
        # TODO: Возможно, вынести в базовый класс 
        return [(x.value, x.name) for x in cls]
