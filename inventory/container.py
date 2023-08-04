import sys

from dependency_injector import providers
from dependency_injector.containers import DeclarativeContainer
from dependency_injector.wiring import Provide, inject  # noqa
from loguru import logger
from loguru_logging_intercept import setup_loguru_logging_intercept
from notion_client import AsyncClient as NotionClient
from peewee import PostgresqlDatabase  # noqa
from playhouse import db_url
from pydantic import BaseSettings, validator
from s3_parse_url import parse_s3_dsn, parse_s3_url
from s3_parse_url.ext.clients import get_boto_client_kwargs
from s3fs import S3FileSystem

from inventory.orm import database


class Settings(BaseSettings):
    postgres_dsn: str
    notion_token: str
    notion_database_id: str
    s3_dsn: str
    s3_public_url: str
    telegram_token: str
    s3_bucket: str = ""
    logging_level: str = "info"

    @validator("s3_bucket")
    def set_s3_bucket(v, values):
        if not v:
            dsn = parse_s3_url(values["s3_dsn"])
            return dsn.bucket_name
        return v


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
    logger.info("Database ready")
    return database


def init_s3fs(dsn: str):
    s3_dsn = parse_s3_dsn(dsn)
    s3fs = S3FileSystem(
        key=s3_dsn.access_key_id,
        secret=s3_dsn.secret_access_key,
        client_kwargs=get_boto_client_kwargs(s3_dsn),
    )
    bucket = s3_dsn.bucket_name
    s3fs.mkdir(f"{bucket}/images")
    return s3fs


class Container(DeclarativeContainer):
    settings: Settings = providers.Configuration()
    logging = providers.Resource(init_logging, level=settings.logging_level)
    database = providers.Resource(init_database, dsn=settings.postgres_dsn)
    notion = providers.Resource(NotionClient, auth=settings.notion_token)
    s3fs = providers.Resource(init_s3fs, dsn=settings.s3_dsn)
