from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CommanderContext:
    symbol: str
    snapshot: Optional[Dict[str, Any]] = None
    recorder_result: Optional[Dict[str, Any]] = None
    behaviour: Any = None
    flow: Any = None
    structure: Any = None
    battle: Any = None
    evidence: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    errors: Dict[str, str] = field(default_factory=dict)

    def set_error(
        self,
        engine_name: str,
        error: Exception,
    ) -> None:
        self.errors[engine_name] = str(error)

    @property
    def ready(self) -> bool:
        return not self.errors
