from logging import basicConfig
from logging.handlers import TimedRotatingFileHandler
from os import path

from dishka import make_container

from cloyt.infrastructure import InfrastructureProvider, DaemonConfig
from cloyt.apps.daemon.synchronizer import CloytSynchronizer


def main():
    container = make_container(InfrastructureProvider())
    config: DaemonConfig = container.get(DaemonConfig)
    basicConfig(
        level=config.logging_level,
        handlers=[
            TimedRotatingFileHandler(
                filename=path.join(config.logs_path, "daemon.log"),
                backupCount=10,
                when="midnight",
            ),
        ],
    )
    app = CloytSynchronizer(container)
    app.run()
