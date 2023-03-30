FROM python:3.9

WORKDIR /root
ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_NO_CACHE_DIR=off
ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV PIP_DEFAULT_TIMEOUT=100
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PATH="$POETRY_HOME/bin:$PATH"

RUN curl -sSL https://install.python-poetry.org | python3 -
COPY pyproject.toml poetry.lock .
RUN poetry install -n --no-ansi --no-root
COPY inventory inventory
COPY main.py .

ENTRYPOINT ["/bin/bash", "-l", "-c"]
CMD ["python main.py"]
