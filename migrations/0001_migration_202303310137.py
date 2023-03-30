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
    class Meta:
        table_name = "user"


