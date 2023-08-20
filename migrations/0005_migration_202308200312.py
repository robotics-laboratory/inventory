# auto-generated snapshot
import datetime

import peewee
from peewee import *

snapshot = Snapshot()


@snapshot.append
class InventoryItem(peewee.Model):
    type = IntegerField()
    name = CharField(max_length=200)
    page_id = UUIDField(null=True)
    quantity = SmallIntegerField(default=0)

    class Meta:
        table_name = "inventory_item"


@snapshot.append
class User(peewee.Model):
    telegram_id = IntegerField(index=True, unique=True)
    full_name = CharField(max_length=200)
    is_admin = BooleanField(default=False)

    class Meta:
        table_name = "user"


def forward(old_orm, new_orm):
    inventoryitem = new_orm["inventoryitem"]
    return [
        # Apply default value 0 to the field inventoryitem.quantity,
        inventoryitem.update({inventoryitem.quantity: 0}).where(
            inventoryitem.quantity.is_null(True)
        ),
    ]
