FROM python:3.11.9-alpine

RUN apk update && apk add curl
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/share/pypoetry/venv/bin/:${PATH}"
COPY . /confuk
WORKDIR /confuk
RUN poetry config virtualenvs.create false \
    && poetry install --with dev
ENTRYPOINT ["/bin/sh"]
