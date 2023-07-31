from inventory import orm
import os
from inventory.bot import init_bot
from inventory.container import (
    Container, 
    Settings, 
    PostgresqlDatabase, 
    Provide,
    inject,
)
from loguru import logger

def init_container():
    container = Container()
    container.settings.postgres_dsn.override(os.environ["POSTGRES_DSN"])
    container.settings.logging_level.override("info")
    container.logging.init()
    container.database.init()
    container.wire(packages=["inventory"])
    return container

def useradd(
    id:int, 
    full_name: str, 
    is_admin: bool,
):

    container = init_container()
    database = container.database()

    with database.transaction():
        total_users = orm.User.select().count()
        logger.info(f"Total users in DB: {total_users}")

        new_user = orm.User(telegram_id = id, full_name = full_name, is_admin = is_admin)
        new_user.save()
        logger.info(f"Username {full_name}, id {id}, is_admin {is_admin} has been added")

    total_users = orm.User.select().count()
    logger.info(f"Total users in DB: {total_users}")
    
def userdel(
        id: int,
):
    
    container = init_container()
    database = container.database()

    with database.transaction():
        logger.info(f"User to be removed: {id}")
        user_to_be_removed = orm.User.select().where(orm.User.telegram_id == id).get()
        user_to_be_removed.delete_instance()

def useredit(
       id:int, 
        new_full_name: str, 
        is_admin: bool,
):

    container = init_container()
    database = container.database()

    with database.transaction():
        edited_user = orm.User.select().where(orm.User.telegram_id == id).get()
        if(new_full_name is not None):
            edited_user.full_name = new_full_name
            logger.info(f"Username {edited_user.full_name} has been assigned to user id {edited_user.telegram_id}" )
        if (is_admin is True):
            logger.info(f"User {edited_user.telegram_id} has been given admin status")
            edited_user.is_admin = is_admin
        elif(is_admin is False):
            logger.info(f"User {edited_user.telegram_id} has been stripped of admin status")
            edited_user.is_admin = is_admin
        edited_user.save()

def userlist(
        is_verbose: bool,
):

    container = init_container()
    database = container.database()

    total_users = orm.User.select().count()
    print(f"Total users in DB: {total_users}")

    if (is_verbose is True):
        print(f"ID \t Full name \t Telegram ID \t ADMIN")
        for user in orm.User.select():
            print(f"{user.id} \t {user.full_name} \t\t {user.telegram_id} \t\t {user.is_admin}")
    elif(is_verbose is False):
        print(f"Full name\t ADMIN")
        for user in orm.User.select():
            print(f"{user.full_name} \t\t {user.is_admin}")

