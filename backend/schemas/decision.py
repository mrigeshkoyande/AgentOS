from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Stakeholder schemas
class StakeholderCreate(BaseModel):
    name: str
    role: str # 'driver', 'contributor', 'approver', 'informed'
    type: Optional[str] = None
    weight: Optional[float] = 1.0
    approval_required: Optional[bool] = False

class StakeholderUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    type: Optional[str] = None
    weight: Optional[float] = None
    approval_required: Optional[bool] = None

class Stakeholder(BaseModel):
    id: str
    decision_id: str
    name: str
    role: str
    type: Optional[str] = None
    weight: float
    approval_required: bool
    created_at: str

# Preference schemas
class PreferenceCreate(BaseModel):
    stakeholder_id: str
    criterion: str
    value: str
    weight: Optional[float] = 1.0
    priority: Optional[str] = 'medium'
    description: Optional[str] = None

class PreferenceUpdate(BaseModel):
    criterion: Optional[str] = None
    value: Optional[str] = None
    weight: Optional[float] = None
    priority: Optional[str] = None
    description: Optional[str] = None

class Preference(BaseModel):
    id: str
    stakeholder_id: str
    criterion: str
    value: str
    weight: float
    priority: str
    description: Optional[str] = None

# Constraint schemas
class ConstraintCreate(BaseModel):
    stakeholder_id: str
    criterion: str
    operator: str # '==', '!=', '>', '<', '>=', '<='
    value: str
    severity: Optional[str] = 'soft' # 'hard', 'soft'

class ConstraintUpdate(BaseModel):
    criterion: Optional[str] = None
    operator: Optional[str] = None
    value: Optional[str] = None
    severity: Optional[str] = None

class Constraint(BaseModel):
    id: str
    stakeholder_id: str
    criterion: str
    operator: str
    value: str
    severity: str

# Options schemas
class DecisionOptionCreate(BaseModel):
    name: str
    description: Optional[str] = None

class DecisionOption(BaseModel):
    id: str
    decision_id: str
    name: str
    description: Optional[str] = None

# Conflict schemas
class ConflictCreate(BaseModel):
    criterion: str
    stakeholder_ids: List[str]
    description: str
    severity: Optional[str] = 'medium'

class Conflict(BaseModel):
    id: str
    decision_id: str
    criterion: str
    stakeholder_ids: List[str]
    description: str
    severity: str
    status: str
    created_at: str
    resolved_at: Optional[str] = None

# Negotiation Round schemas
class NegotiationRoundCreate(BaseModel):
    round_number: int
    proposal: str
    counter_proposal: Optional[str] = None
    reason: Optional[str] = None

class NegotiationRound(BaseModel):
    id: str
    decision_id: str
    round_number: int
    status: str
    proposal: str
    counter_proposal: Optional[str] = None
    reason: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None

# Decision Vote schemas
class DecisionVoteCreate(BaseModel):
    stakeholder_id: str
    option_id: str
    score: float
    reason: Optional[str] = None

class DecisionVote(BaseModel):
    id: str
    decision_id: str
    stakeholder_id: str
    option_id: str
    score: float
    reason: Optional[str] = None

# Decision Outcome schemas
class DecisionOutcomeCreate(BaseModel):
    selected_option: str
    consensus_score: float
    rationale: str
    tradeoffs: Optional[str] = None
    dissent: Optional[str] = None
    next_actions: Optional[str] = None

class DecisionOutcome(BaseModel):
    id: str
    decision_id: str
    selected_option: str
    consensus_score: float
    rationale: str
    tradeoffs: Optional[str] = None
    dissent: Optional[str] = None
    next_actions: Optional[str] = None
    created_at: str

# Decision schemas
class DecisionCreate(BaseModel):
    session_id: str
    title: str
    description: Optional[str] = None
    strategy: Optional[str] = 'consensus'
    deadline: Optional[str] = None
    consensus_threshold: Optional[float] = 0.7
    max_rounds: Optional[int] = 5
    compromise_allowed: Optional[bool] = True
    approval_required: Optional[bool] = True

class DecisionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    strategy: Optional[str] = None
    deadline: Optional[str] = None
    consensus_threshold: Optional[float] = None
    max_rounds: Optional[int] = None
    compromise_allowed: Optional[bool] = None
    approval_required: Optional[bool] = None

class Decision(BaseModel):
    id: str
    session_id: str
    title: str
    description: Optional[str] = None
    status: str
    strategy: str
    deadline: Optional[str] = None
    consensus_threshold: float
    max_rounds: int
    compromise_allowed: bool
    approval_required: bool
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    stakeholders: List[Stakeholder] = []
    options: List[DecisionOption] = []
    conflicts: List[Conflict] = []
    negotiation_rounds: List[NegotiationRound] = []
    votes: List[DecisionVote] = []
    outcome: Optional[DecisionOutcome] = None

# Approval schemas
class ApprovalRequest(BaseModel):
    stakeholder_id: str
    action: str # 'approve', 'reject', 'request_changes'
    reason: Optional[str] = None

# Simulate Request
class SimulateRequest(BaseModel):
    preferences: Optional[List[PreferenceCreate]] = None
    constraints: Optional[List[ConstraintCreate]] = None
    options: Optional[List[DecisionOptionCreate]] = None
