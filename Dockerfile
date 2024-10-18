FROM python:3.12

WORKDIR /usr/local/src/cloyt
RUN pip install pip-tools
COPY pyproject.toml .
RUN pip-compile
RUN pip install -r requirements.txt
COPY . .
RUN pip install -e . --no-deps --no-cache-dir
