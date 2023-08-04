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
    return container


def useradd(
    id: int,
    full_name: str,
    is_admin: bool,
):
    init_container()
    total_users = orm.User.select().count()
    logger.info(f"Total users in DB: {total_users}")

    new_user = orm.User(telegram_id=id, full_name=full_name, is_admin=is_admin)
    new_user.save()
    logger.info(f"Username {full_name}, id {id}, is_admin {is_admin} has been added")

    total_users = orm.User.select().count()
    logger.info(f"Total users in DB: {total_users}")


def userdel(id: int):
    init_container()
    logger.info(f"User to be removed: {id}")
    user_to_be_removed = orm.User.select().where(orm.User.telegram_id == id).get()
    user_to_be_removed.delete_instance()


def useredit(
    id: int,
    new_full_name: Optional[str],
    is_admin: Optional[str],
):
    init_container()
    edited_user = orm.User.select().where(orm.User.telegram_id == id).get()
    if new_full_name is not None:
        edited_user.full_name = new_full_name
        logger.info(f"Username: {edited_user.full_name}")
    is_admin = parse_obj_as(Optional[bool], is_admin)
    if is_admin is not None:
        edited_user.is_admin = is_admin
        logger.info(f"User's admin status was changed to: {is_admin}")
    edited_user.save()


def userlist(
    is_verbose: bool,
):
    init_container()

    total_users = orm.User.select().count()
    logger.info(f"Total users in DB: {total_users}")

    if is_verbose is True:
        logger.info("ID   Full name                Telegram ID              ADMIN")
        for user in orm.User.select():
            logger.info(
                f"{user.id:<5}{user.full_name:<25}{user.telegram_id:<25}{user.is_admin}"
            )
    elif is_verbose is False:
        logger.info("NAME                     ADMIN")
        for user in orm.User.select():
            logger.info(f"{user.full_name:<25}{user.is_admin}")
