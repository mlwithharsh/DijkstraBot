import logging
from datetime import datetime
import structlog
from rich.logging import RichHandler
from rich.console import Console
import os

def setup_logger(log_level="INFO"):
    if not os.path.exists("logs"):
        os.makedirs("logs")
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = f"logs/dijkstrabot_{date_str}.jsonl"

    # Check if we are running in a web context
    is_web = os.getenv("RUN_CONTEXT") == "web"

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.WriteLoggerFactory(file=open(log_file, "a", encoding="utf-8")),
        cache_logger_on_first_use=True,
    )

    handlers = [RichHandler(rich_tracebacks=True, console=Console(stderr=True))]

    logging.basicConfig(level=log_level, format="%(message)s", datefmt="[%X]", handlers=handlers)
    return structlog.get_logger()

logger = setup_logger()
