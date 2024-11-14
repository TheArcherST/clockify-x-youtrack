from os import path
from logging import basicConfig
from logging.handlers import TimedRotatingFileHandler
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka

from cloyt.infrastructure import InfrastructureProvider, AdminConfig
from cloyt.apps.admin.views import setup_admin


def main():

    container = make_async_container(InfrastructureProvider())

    @asynccontextmanager
    async def fastapi_admin_setup(app_):
        config: AdminConfig = await container.get(AdminConfig)
        basicConfig(
            level=config.logging_level,
            handlers=[
                TimedRotatingFileHandler(
                    filename=path.join(config.logs_path, "admin.log"),
                    backupCount=10,
                    when="midnight",
                ),
            ],
            format="[%(asctime)s] [%(levelname)s] - %(name)s - %(message)s",
        )
        await setup_admin(container, app_)
        yield

    app = FastAPI(
        title="Cloyt",
        lifespan=fastapi_admin_setup,
    )
    setup_dishka(container, app)

    uvicorn.run(
        app,
        port=80,
        host="0.0.0.0",
        forwarded_allow_ips=["*"],  # todo: adjust
    )
