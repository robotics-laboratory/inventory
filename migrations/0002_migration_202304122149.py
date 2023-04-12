# auto-generated snapshot
from peewee import *
import datetime
import peewee


snapshot = Snapshot()


@snapshot.append
class InventoryItem(peewee.Model):
    type = IntegerField()
    name = CharField(max_length=200)
    class Meta:
        table_name = "inventory_item"


@snapshot.append
class User(peewee.Model):
    name = CharField(max_length=200)
    telegram_id = IntegerField(index=True, unique=True)
    isAdmin = BooleanField()
    class Meta:
        table_name = "user"


def forward(old_orm, new_orm):
    user = new_orm['user']
    return [
        # Apply default value False to the field user.isAdmin,
        user.update({user.isAdmin: False}).where(user.isAdmin.is_null(True)),
    ]
