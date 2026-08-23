"""Validate security-related settings at application startup."""

import logging
import os
import stat

from app.config import DATA_DIR, DOCUMENTS_DIR, DEFAULT_ADMIN_PASSWORD, DEFAULT_SECRET_KEY, settings

logger = logging.getLogger(__name__)


def validate_settings() -> None:
    weak_secret = (
        len(settings.secret_key) < 32
        or settings.secret_key == DEFAULT_SECRET_KEY
        or "change-me" in settings.secret_key.lower()
    )
    weak_admin = (
        settings.admin_password == DEFAULT_ADMIN_PASSWORD
        and not settings.admin_password_hash
    )

    if settings.is_production:
        if weak_secret:
            raise RuntimeError(
                "Production requires SECRET_KEY of at least 32 characters (not the default)."
            )
        if weak_admin:
            raise RuntimeError(
                "Production requires ADMIN_PASSWORD_HASH or a non-default ADMIN_PASSWORD."
            )
    else:
        if weak_secret:
            logger.warning("Using a weak SECRET_KEY — set a strong key before production.")
        if weak_admin:
            logger.warning("Using default admin credentials — change before production.")


def ensure_data_directory_permissions() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    if not settings.is_production:
        return

    try:
        os.chmod(DATA_DIR, stat.S_IRWXU)
        if os.name != "nt":
            mode = os.stat(DATA_DIR).st_mode
            if mode & stat.S_IRWXG or mode & stat.S_IRWXO:
                logger.warning("data/ directory is readable by group or others — restrict permissions.")
    except OSError as exc:
        logger.warning("Could not set data directory permissions: %s", exc)
