from logging import basicConfig
from logging.handlers import RotatingFileHandler
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
            RotatingFileHandler(
                filename=path.join(config.logs_path, "daemon.log"),
                maxBytes=1000 * 1000,
                backupCount=10,
            ),
        ],
    )
    app = CloytSynchronizer(container)
    app.run()
