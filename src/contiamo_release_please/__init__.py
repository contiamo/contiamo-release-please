"""Contiamo Release Please - Automated semantic versioning and release management."""

from importlib.metadata import version

try:
    __version__ = version("contiamo-release-please")
except Exception:
    __version__ = "0.0.0-dev"
