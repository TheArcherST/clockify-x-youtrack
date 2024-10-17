from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka

from cloyt.infrastructure import InfrastructureProvider
from cloyt.apps.admin.views import setup_admin


async def do_async():
    @asynccontextmanager
    async def fastapi_admin_setup():
        container = make_async_container(InfrastructureProvider())
        setup_dishka(container, app)
        await setup_admin(container, app)

    app = FastAPI(
        title="Cloyt",
        lifespan=fastapi_admin_setup,
    )

    uvicorn.run(
        app,
    )
