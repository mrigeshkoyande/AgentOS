from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class Preference(BaseModel):
    criterion: str
    value: Any
    weight: float = Field(default=1.0, ge=0.0)
    priority: Optional[str] = None
    strategy: str = "exact"  # exact, higher_is_better, lower_is_better, contains, range
    min_value: Optional[float] = None
    max_value: Optional[float] = None

class Constraint(BaseModel):
    criterion: str
    operator: str  # =, ==, !=, >, >=, <, <=, contains, must_include
    value: Any
    type: str = "HARD"  # HARD, SOFT
    penalty: float = Field(default=0.1, ge=0.0)

class Option(BaseModel):
    id: str
    name: str
    attributes: Dict[str, Any]

class Stakeholder(BaseModel):
    id: str
    name: str
    weight: float = Field(default=1.0, ge=0.0)
    preferences: List[Preference] = []
