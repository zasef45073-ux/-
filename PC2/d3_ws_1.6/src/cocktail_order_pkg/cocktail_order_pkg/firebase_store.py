import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import firebase_admin
from firebase_admin import credentials, db

try:
    from ament_index_python.packages import get_package_share_directory
except Exception:
    get_package_share_directory = None


def _is_enabled(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


class FirebaseOrderStore:
    """Firebase Realtime Database helper for order and cleanup events."""

    def __init__(
        self,
        enabled: Optional[bool] = None,
        key_path: Optional[str] = None,
        database_url: Optional[str] = None,
        orders_path: Optional[str] = None,
        cleanup_path: Optional[str] = None,
    ) -> None:
        if enabled is None:
            enabled = _is_enabled(os.getenv("FIREBASE_ENABLED", "false"))

        self.enabled = enabled
        self.database_url = database_url or os.getenv("FIREBASE_DATABASE_URL", "")
        self.key_path = key_path or os.getenv(
            "FIREBASE_KEY_PATH", "resource/serviceAccountKey.json"
        )
        self.orders_path = orders_path or os.getenv("FIREBASE_ORDERS_PATH", "orders")
        self.cleanup_path = cleanup_path or os.getenv(
            "FIREBASE_CLEANUP_PATH", "cleanup_events"
        )

        self._initialized = False
        self._lock = threading.Lock()

    def _resolve_key_path(self) -> str:
        if os.path.isabs(self.key_path):
            return self.key_path

        candidates = [os.path.abspath(self.key_path)]

        if get_package_share_directory is not None:
            try:
                share_dir = get_package_share_directory("cocktail_order_pkg")
                candidates.append(os.path.join(share_dir, self.key_path))
                if self.key_path.startswith("resource/"):
                    candidates.append(
                        os.path.join(share_dir, self.key_path.split("resource/", 1)[1])
                    )
            except Exception:
                pass

        module_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(module_dir, self.key_path))
        candidates.append(os.path.join(module_dir, "resource", "serviceAccountKey.json"))

        for path in candidates:
            if os.path.exists(path):
                return path

        return os.path.abspath(self.key_path)

    def initialize(self) -> bool:
        if not self.enabled:
            return False

        with self._lock:
            if self._initialized:
                return True

            if not self.database_url:
                return False

            key_path = self._resolve_key_path()
            if not os.path.exists(key_path):
                return False

            if not firebase_admin._apps:
                cred = credentials.Certificate(key_path)
                firebase_admin.initialize_app(cred, {"databaseURL": self.database_url})

            self._initialized = True
            return True

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def save_order(self, payload: Dict[str, Any]) -> Optional[str]:
        """Push an order record. Returns generated firebase key or None."""
        if not self.initialize():
            return None

        data = dict(payload)
        data.setdefault("created_at", self._now_iso())
        pushed = db.reference(self.orders_path).push(data)
        return pushed.key

    def update_order_status(self, order_key: str, status: str) -> bool:
        """Update robot status for a specific order key."""
        if not self.initialize():
            return False

        db.reference(f"{self.orders_path}/{order_key}/robot_status").set(status)
        db.reference(f"{self.orders_path}/{order_key}/updated_at").set(self._now_iso())
        return True

    def save_cleanup_event(self, payload: Dict[str, Any]) -> Optional[str]:
        """Push a cleanup event record. Returns generated key or None."""
        if not self.initialize():
            return None

        data = dict(payload)
        data.setdefault("created_at", self._now_iso())
        pushed = db.reference(self.cleanup_path).push(data)
        return pushed.key


_firebase_store_singleton: Optional[FirebaseOrderStore] = None
_firebase_store_lock = threading.Lock()


def get_firebase_store() -> FirebaseOrderStore:
    global _firebase_store_singleton
    with _firebase_store_lock:
        if _firebase_store_singleton is None:
            _firebase_store_singleton = FirebaseOrderStore()
        return _firebase_store_singleton
