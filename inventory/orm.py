import peewee

from inventory.enums import ItemType
from peewee import fn  # noqa

# Lazy initialization - see container.py > init_database
# https://docs.peewee-orm.com/en/latest/peewee/database.html#run-time-database-configuration
database = peewee.PostgresqlDatabase(None)


class ORMBase(peewee.Model):
    class Meta:
        database = database
        legacy_table_names = False


class User(ORMBase):
    id = peewee.AutoField()
    name = peewee.CharField(200)
    telegram_id = peewee.IntegerField(unique=True, index=True)


class InventoryItem(ORMBase):
    id = peewee.AutoField()
    type = peewee.IntegerField(choices=ItemType.choices())
    name = peewee.CharField(200)
