from loguru_logging_intercept import setup_loguru_logging_intercept
from dependency_injector.containers import DeclarativeContainer
from dependency_injector import providers
from dependency_injector.wiring import Provide, inject  # noqa
from pydantic import BaseSettings
from inventory.orm import database
from playhouse import db_url
from loguru import logger
import sys


class Settings(BaseSettings):
    postgres_dsn: str = None
    notion_dsn: str = None
    telegram_token: str = None
    logging_level: str = "info"


def init_logging(level: str):
    logger.remove()
    logger.add(sys.stderr, level=level.upper())
    setup_loguru_logging_intercept(level=level.upper())
    logger.info(f"Logging ready (level: {level.lower()})")


def init_database(dsn: str):
    parsed = db_url.urlparse(dsn)
    connect_kwargs = db_url.parseresult_to_dict(parsed)
    database.init(**connect_kwargs)
    database.connect()
    logger.info(f"Database ready")


class Container(DeclarativeContainer):
    settings: Settings = providers.Configuration()
    logging = providers.Resource(init_logging, level=settings.logging_level)
    database = providers.Resource(init_database, dsn=settings.postgres_dsn)
