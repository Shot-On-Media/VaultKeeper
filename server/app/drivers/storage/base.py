from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class StorageValidationResult:
    valid: bool
    message: str


StorageValidator = Callable[[dict[str, object]], StorageValidationResult]
