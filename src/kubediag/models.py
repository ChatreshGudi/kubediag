from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class Evidence:
    namespace: str
    name: str
    kind: str
    container_name: Optional[str] = None
    phase: Optional[str] = None
    state: Optional[str] = None
    restart_count: Optional[int] = None
    exit_code: Optional[int] = None
    termination_reason: Optional[str] = None
    events: List[Dict[str, str]] = field(default_factory=list)
    logs: Optional[str] = None
    requests: Optional[Dict[str, str]] = None
    limits: Optional[Dict[str, str]] = None
    node_conditions: List[Dict[str, str]] = field(default_factory=list)

@dataclass
class Incident:
    type: str
    severity: str
    description: str
    evidence: Evidence
