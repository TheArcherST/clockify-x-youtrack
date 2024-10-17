from dishka import Provider, provide, Scope
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import (
    create_engine,
    Engine,
)
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
)


class PostgresConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str
    
    def get_sqlalchemy_url(self, driver: str):
        return "postgres+{}://{}:{}/{}:{}/{}".format(
            driver,
            self.user,
            self.password,
            self.host,
            self.port,
            self.database,
        )


class AdminConfig(BaseModel):
    host: str
    port: int


class DaemonConfig(BaseModel):
    sync_throttling_delay_seconds: int
    sync_window_size: int


class CloytConfig(BaseSettings):
    postgres: PostgresConfig | None = None
    admin: AdminConfig | None = None
    daemon: DaemonConfig | None = None

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_prefix="CLOYT__",
    )


class InfrastructureProvider(Provider):
    @provide(scope=Scope.APP)
    def get_config(self) -> CloytConfig:
        return CloytConfig()

    @provide(scope=Scope.APP)
    def get_postgres_config(
            self,
            config: CloytConfig,
    ) -> PostgresConfig:
        if config.postgres is None:
            raise RuntimeError("Postgres configuration not found")

        return config.postgres

    @provide(scope=Scope.APP)
    def get_admin_config(
            self,
            config: CloytConfig,
    ) -> AdminConfig:
        if config.admin is None:
            raise RuntimeError("Admin panel configuration not found")

        return config.admin

    @provide(scope=Scope.APP)
    def get_daemon_config(
            self,
            config: CloytConfig,
    ) -> DaemonConfig:
        if config.daemon is None:
            raise RuntimeError("Daemon configuration not found.")

        return config.daemon

    @provide(scope=Scope.APP)
    async def get_async_engine(
            self,
            postgres_config: PostgresConfig,
    ) -> AsyncEngine:
        return create_async_engine(
            postgres_config.get_sqlalchemy_url("asyncpg"),
        )

    @provide(scope=Scope.REQUEST)
    async def get_async_session(
            self,
            engine: AsyncEngine,
    ) -> AsyncSession:
        async with AsyncSession(bind=engine) as session:
            yield session

    @provide(scope=Scope.APP)
    def get_sync_engine(
            self,
            postgres_config: PostgresConfig,
    ) -> Engine:
        return create_engine(
            postgres_config.get_sqlalchemy_url("psycopg"),
        )

    @provide(scope=Scope.REQUEST)
    def get_sync_session(
            self,
            engine: Engine
    ) -> Session:
        with Session(bind=engine) as session:
            yield session
