from functools import lru_cache

from app.core.config import get_settings
from app.storage.local import LocalStorage


@lru_cache
def get_storage() -> LocalStorage:
    return LocalStorage(get_settings().upload_dir)
