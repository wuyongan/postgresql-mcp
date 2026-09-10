"""File system watcher for hot-plug tool discovery."""

import asyncio
import logging
import time
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class ToolFileWatcher:
    """Monitors the tools/ directory for file changes and triggers reloads."""

    def __init__(self, tools_dir: Path, loader):
        """
        Args:
            tools_dir: Path to the tools directory.
            loader: A ToolLoader instance.
        """
        self._tools_dir = tools_dir
        self._loader = loader
        self._running = False
        self._thread = None
        self._poll_interval = 2.0  # seconds between polls
        self._last_mtimes: dict[str, float] = {}

    async def start(self):
        """Start the watcher (runs in background thread)."""
        if not self._tools_dir.is_dir():
            logger.warning("Tools directory not found: %s", self._tools_dir)
            return

        logger.info("Starting file watcher for %s", self._tools_dir)

        # Initialize mtime tracking
        self._scan_mtimes()

        # Create a thread-safe event loop for async callbacks
        self._running = True
        self._thread = threading.Thread(
            target=self._watch_loop,
            name="tool-watcher",
            daemon=True,
        )
        self._thread.start()

    async def stop(self):
        """Stop the watcher."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("File watcher stopped")

    def _scan_mtimes(self):
        """Scan all .py files and record their modification times."""
        if not self._tools_dir.is_dir():
            return
        for f in self._tools_dir.iterdir():
            if f.is_file() and f.suffix == ".py" and not f.name.startswith("_"):
                if f.name not in ("loader.py", "watcher.py"):
                    self._last_mtimes[str(f)] = f.stat().st_mtime

    def _watch_loop(self):
        """Background thread: poll for file changes."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self._running:
            try:
                self._check_changes()
                time.sleep(self._poll_interval)
            except Exception as e:
                logger.error("Watcher error: %s", e)

        loop.close()

    def _check_changes(self):
        """Check for file modifications and trigger reloads."""
        if not self._tools_dir.is_dir():
            return

        current_mtimes: dict[str, float] = {}
        for f in self._tools_dir.iterdir():
            if f.is_file() and f.suffix == ".py" and not f.name.startswith("_"):
                if f.name not in ("loader.py", "watcher.py"):
                    current_mtimes[str(f)] = f.stat().st_mtime

        # Detect new files
        for path, mtime in current_mtimes.items():
            if path not in self._last_mtimes:
                module_name = Path(path).stem
                logger.info("New tool file detected: %s", module_name)
                self._on_file_added(path)

        # Detect modified files
        for path, mtime in current_mtimes.items():
            if path in self._last_mtimes:
                if mtime > self._last_mtimes[path]:
                    module_name = Path(path).stem
                    logger.info("Tool file modified: %s", module_name)
                    self._on_file_modified(path)

        # Detect deleted files
        for path in self._last_mtimes:
            if path not in current_mtimes:
                module_name = Path(path).stem
                logger.info("Tool file removed: %s", module_name)
                self._on_file_removed(path)

        self._last_mtimes = current_mtimes

    def _on_file_added(self, path: str):
        """Handle new file detection."""
        module_name = Path(path).stem
        try:
            count = self._loader.register_module(module_name)
            if count > 0:
                logger.info("Registered %d tool(s) from %s", count, module_name)
        except Exception:
            logger.exception("Failed to load tool from %s", module_name)

    def _on_file_modified(self, path: str):
        """Handle file modification detection."""
        module_name = Path(path).stem
        try:
            self._loader.reload_module(module_name)
        except Exception:
            logger.exception("Failed to reload tool from %s", module_name)

    def _on_file_removed(self, path: str):
        """Handle file removal detection."""
        module_name = Path(path).stem
        try:
            self._loader.unregister_module(module_name)
        except Exception:
            logger.exception("Failed to unregister tool from %s", module_name)


def create_file_watcher(tools_dir: Path, loader):
    """Create a ToolFileWatcher instance."""
    return ToolFileWatcher(tools_dir, loader)
