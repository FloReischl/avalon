"""Logging setup for the standalone Avalo server."""

import logging


def configure_logging(log_path: str) -> None:
    """Configure Avalo server logging."""
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    )

    logger = logging.getLogger("server")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
