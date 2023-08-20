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
class Relation(peewee.Model):
    parent = snapshot.ForeignKeyField(
        backref="children", index=True, model="inventoryitem"
    )
    child = snapshot.ForeignKeyField(
        backref="parents", index=True, model="inventoryitem"
    )

    class Meta:
        table_name = "relation"
        indexes = (
            peewee.Index(
                name="relation_unique_pairs",
                table=peewee.Table(name="relation"),
                expressions=[
                    peewee.SQL("LEAST(parent_id, child_id)", None),
                    peewee.SQL("GREATEST(parent_id, child_id)", None),
                ],
                unique=True,
                safe=True,
            ),
        )
        primary_key = peewee.CompositeKey("parent", "child")


@snapshot.append
class User(peewee.Model):
    telegram_id = IntegerField(index=True, unique=True)
    full_name = CharField(max_length=200)
    is_admin = BooleanField(default=False)

    class Meta:
        table_name = "user"
