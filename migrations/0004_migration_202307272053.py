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
    telegram_id = IntegerField(index=True, unique=True)
    full_name = CharField(max_length=200)
    is_admin = BooleanField(default=False)
    class Meta:
        table_name = "user"


def forward(old_orm, new_orm):
    user = new_orm['user']
    return [
        # Apply default value '' to the field user.full_name,
        user.update({user.full_name: ''}).where(user.full_name.is_null(True)),
    ]


def backward(old_orm, new_orm):
    user = new_orm['user']
    return [
        # Apply default value '' to the field user.name,
        user.update({user.name: ''}).where(user.name.is_null(True)),
    ]
