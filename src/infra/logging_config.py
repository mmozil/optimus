"""
Agent Optimus — Structured Logging.
JSON-formatted logging with context, rotation, and Telegram alerting.
"""

import logging
import logging.handlers
import sys
from pathlib import Path

try:
    from pythonjsonlogger import json as jsonlogger
except ImportError:
    jsonlogger = None


def setup_logging(
    level: str = "INFO",
    log_file: str | None = "logs/optimus.log",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    json_format: bool = True,
):
    """
    Configure structured logging for the entire application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None = stdout only)
        max_bytes: Max log file size before rotation
        backup_count: Number of rotated files to keep
        json_format: Use JSON format (True) or plain text (False)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # ─────────────────────────────────────────
    # JSON Formatter
    # ─────────────────────────────────────────
    if json_format and jsonlogger:
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger",
            },
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    else:
        if json_format and not jsonlogger:
            logging.warning("python-json-logger not installed, falling back to plain text logs")
        formatter = logging.Formatter(
            fmt="%(asctime)s │ %(levelname)-8s │ %(name)-30s │ %(message)s",
            datefmt="%H:%M:%S",
        )

    # ─────────────────────────────────────────
    # Console Handler (stdout)
    # ─────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # ─────────────────────────────────────────
    # File Handler (with rotation)
    # ─────────────────────────────────────────
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # ─────────────────────────────────────────
    # Error File Handler (errors only)
    # ─────────────────────────────────────────
    if log_file:
        error_path = log_path.parent / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            filename=str(error_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)

    # Suppress noisy third-party loggers
    for noisy in ["httpx", "httpcore", "uvicorn.access", "asyncio"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


class TelegramAlertHandler(logging.Handler):
    """
    Send CRITICAL log entries to Telegram as alerts.
    Only fires for ERROR and CRITICAL levels.
    """

    def __init__(self, bot_token: str, chat_id: str, level: int = logging.ERROR):
        super().__init__(level)
        self.bot_token = bot_token
        self.chat_id = chat_id

    def emit(self, record: logging.LogRecord):
        try:
            import httpx

            message = (
                f"🚨 *Agent Optimus Alert*\n"
                f"Level: `{record.levelname}`\n"
                f"Logger: `{record.name}`\n"
                f"Message: {record.getMessage()[:500]}"
            )

            httpx.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                },
                timeout=5,
            )
        except Exception:
            pass  # Never let alerting break the app


def add_telegram_alerts(bot_token: str, chat_id: str):
    """Add Telegram alert handler for critical errors."""
    handler = TelegramAlertHandler(bot_token, chat_id)
    logging.getLogger().addHandler(handler)
