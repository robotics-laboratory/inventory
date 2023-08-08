import peewee
from peewee import fn  # noqa

from inventory.enums import ItemType

# Lazy initialization - see container.py > init_database
# https://docs.peewee-orm.com/en/latest/peewee/database.html#run-time-database-configuration
database = peewee.PostgresqlDatabase(None)


class ORMBase(peewee.Model):
    class Meta:
        database = database
        legacy_table_names = False

    def __str__(self):
        model_fields = self._meta.sorted_fields
        fields = [f"{f.name}: {getattr(self, f.name, 'n/a')!r}" for f in model_fields]
        return f"{self.__class__.__name__}({', '.join(fields)})"

    def __repr__(self):
        return str(self)


class User(ORMBase):
    id = peewee.AutoField()
    telegram_id = peewee.IntegerField(unique=True, index=True)
    full_name = peewee.CharField(200)
    is_admin = peewee.BooleanField(default=False)


class InventoryItem(ORMBase):
    id = peewee.AutoField()
    type = peewee.IntegerField(choices=ItemType.choices())
    name = peewee.CharField(200)
