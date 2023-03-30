import os


def pem_bootstrap():
    # Helper function to init database for peewee-migrations util (pem). Works by
    # initializing only container.database resource. Also directly imported to prevent
    # potential circular imports in the future.
    from inventory.container import Container

    container = Container()
    container.settings.logging_level.override("info")
    container.settings.postgres_dsn.override(os.environ["POSTGRES_DSN"])
    container.logging.init()
    container.database.init()
    container.wire(modules=["inventory.orm"])
