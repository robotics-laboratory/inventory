import os
from typing import Optional

from loguru import logger
from pydantic import parse_obj_as

from inventory import orm
from inventory.container import Container


def init_container():
    container = Container()
    container.settings.postgres_dsn.override(os.environ["POSTGRES_DSN"])
    container.settings.logging_level.override("info")
    container.logging.init()
    container.database.init()
    container.wire(packages=["inventory"])


def print_total_users():
    total_users = orm.User.select().count()
    logger.info(f"Total users in DB: {total_users}")


def user_add(id: int, full_name: str, is_admin: bool):
    init_container()
    new_user = orm.User(telegram_id=id, full_name=full_name, is_admin=is_admin)
    new_user.save()
    logger.info(f"Added user: {new_user}")
    print_total_users()


def user_del(id: int):
    init_container()
    user_to_be_removed = orm.User.select().where(orm.User.telegram_id == id).get()
    user_to_be_removed.delete_instance()
    logger.info(f"Removed user: {user_to_be_removed}")
    print_total_users()


def user_edit(id: int, new_full_name: Optional[str], is_admin: Optional[str]):
    init_container()
    edited_user = orm.User.select().where(orm.User.telegram_id == id).get()
    logger.info(f"Before: {edited_user}")
    if new_full_name is not None:
        edited_user.full_name = new_full_name
    is_admin = parse_obj_as(Optional[bool], is_admin)
    if is_admin is not None:
        edited_user.is_admin = is_admin
    logger.info(f"Updated: {edited_user}")
    edited_user.save()


def user_list():
    init_container()
    print_total_users()

    fmt = "{:<5} | {:<25} | {:<25} | {}"
    logger.info(fmt.format("ID", "Full Name", "Telegram ID", "Is Admin"))
    for user in orm.User.select():
        row = fmt.format(user.id, user.full_name, user.telegram_id, user.is_admin)
        logger.info(row)
