# Inventory Management System

## Quick Start

1. Install [poetry](https://python-poetry.org/docs/#installation) and project requirements  with `poetry install`. It will automatically create python virtualenv and manage python requirements for you.

2. Create `.env` file with following variables:
```
COMPOSE_PROJECT_NAME="inventory"
POSTGRES_DSN="postgresql://postgres:postgres@localhost:5432/main"
TELEGRAM_TOKEN="<your telegram bot token>"
```

3. Run docker compose (postgres only): `docker compose --env-file .env up postgres --build -d`. Now you have a postgres instance running on `localhost:5432`. If the port is busy,
try another - replace it both in `docker-compose.yml` and `.env`.

4. Run migrations for postgres: `poetry run pem migrate`.

5. Run python application locally (without docker): `poetry run python main.py`. It's recommended to always use `poetry run` instead of `poetry shell` because it ensures that environment variables from `.env` are always reloaded.

6. To deploy entire stack (postgresql + python app) on a remote server, configure [docker context](https://docs.docker.com/engine/context/working-with-contexts/) and deploy as usual: `docker --context <your server> compose --env-file .env up --build -d`.

## Technologies Used

- Python 3.9
- PostgreSQL 15
- [Poetry](https://python-poetry.org/docs/)
- [Peewee ORM](http://docs.peewee-orm.com/en/latest/)
- [Python-Telegram-Bot](https://python-telegram-bot.org/)
- [Dependency Injector](https://python-dependency-injector.ets-labs.org/)
- [Pydantic](https://docs.pydantic.dev/)
- [Loguru](https://github.com/Delgan/loguru)
