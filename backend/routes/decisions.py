from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from typing import List, Optional
from schemas.decision import (
    DecisionCreate, DecisionUpdate, Decision,
    StakeholderCreate, StakeholderUpdate, Stakeholder,
    PreferenceCreate, PreferenceUpdate, Preference,
    ConstraintCreate, ConstraintUpdate, Constraint,
    DecisionOptionCreate, DecisionOption,
    Conflict, NegotiationRound, DecisionVote, DecisionOutcome,
    ApprovalRequest, SimulateRequest
)
from services.decision_service import DecisionService
from repositories.decision_repository import DecisionRepository
from services.negotiation.negotiation_engine import NegotiationEngine

router = APIRouter(prefix="/api", tags=["decisions"])
service = DecisionService()
repo = DecisionRepository()

# --- Decisions ---

@router.post("/decisions", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_decision(payload: DecisionCreate):
    try:
        decision_id = service.create_decision(
            session_id=payload.session_id,
            title=payload.title,
            description=payload.description,
            strategy=payload.strategy or "consensus",
            deadline=payload.deadline,
            consensus_threshold=payload.consensus_threshold or 0.7,
            max_rounds=payload.max_rounds or 5,
            compromise_allowed=payload.compromise_allowed if payload.compromise_allowed is not None else True,
            approval_required=payload.approval_required if payload.approval_required is not None else True
        )
        return {"id": decision_id, "status": "DRAFT", "message": "Decision created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# --- History ---

@router.get("/decisions/history", response_model=List[dict])
def get_decisions_history():
    return repo.get_history()

@router.get("/decisions/history/{id}", response_model=Decision)
def get_historical_decision(id: str):
    dec = repo.get_decision(id)
    if not dec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision history record not found")
    return dec

@router.get("/decisions/{id}", response_model=Decision)
def get_decision(id: str):
    dec = repo.get_decision(id)
    if not dec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    return dec

@router.patch("/decisions/{id}", response_model=dict)
async def update_decision(id: str, payload: DecisionUpdate):
    dec = repo.get_decision(id)
    if not dec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    
    update_data = payload.model_dump(exclude_unset=True)
    
    # If updating status, go through the service validation
    if "status" in update_data:
        try:
            next_status = update_data.pop("status")
            await service.update_status(id, next_status)
        except (ValueError, PermissionError) as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if update_data:
        # Only allow config updates in DRAFT or SETUP states
        if dec["status"] not in ["DRAFT", "SETUP"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update configuration details after execution starts"
            )
        repo.update_decision(id, update_data)
        
    return {"status": "success", "message": "Decision updated successfully"}

@router.delete("/decisions/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_decision(id: str):
    dec = repo.get_decision(id)
    if not dec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    if dec["status"] not in ["DRAFT", "SETUP"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete decision that is already running or completed"
        )
    repo.delete_decision(id)
    return None

# --- Stakeholders ---

@router.post("/decisions/{id}/stakeholders", response_model=dict, status_code=status.HTTP_201_CREATED)
def add_stakeholder(id: str, payload: StakeholderCreate):
    dec = repo.get_decision(id)
    if not dec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    if dec["status"] not in ["DRAFT", "SETUP"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify stakeholders after execution starts")
    
    if payload.role not in ["driver", "contributor", "approver", "informed"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid stakeholder role '{payload.role}'")
    if payload.weight <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stakeholder weight must be positive")

    stk_id = repo.add_stakeholder(
        decision_id=id,
        name=payload.name,
        role=payload.role,
        stk_type=payload.type,
        weight=payload.weight,
        approval_required=payload.approval_required
    )
    return {"id": stk_id, "message": "Stakeholder added successfully"}

@router.get("/decisions/{id}/stakeholders", response_model=List[Stakeholder])
def get_stakeholders(id: str):
    dec = repo.get_decision(id)
    if not dec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    return dec.get("stakeholders", [])

@router.patch("/stakeholders/{id}", response_model=dict)
def update_stakeholder(id: str, payload: StakeholderUpdate):
    stk = repo.get_stakeholder(id)
    if not stk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stakeholder not found")
    
    dec = repo.get_decision(stk["decision_id"])
    if dec["status"] not in ["DRAFT", "SETUP"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify stakeholders after execution starts")

    update_data = payload.model_dump(exclude_unset=True)
    if "role" in update_data and update_data["role"] not in ["driver", "contributor", "approver", "informed"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid stakeholder role '{update_data['role']}'")
    if "weight" in update_data and update_data["weight"] <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stakeholder weight must be positive")

    repo.update_stakeholder(id, update_data)
    return {"status": "success", "message": "Stakeholder updated successfully"}

@router.delete("/stakeholders/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stakeholder(id: str):
    stk = repo.get_stakeholder(id)
    if not stk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stakeholder not found")
    
    dec = repo.get_decision(stk["decision_id"])
    if dec["status"] not in ["DRAFT", "SETUP"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify stakeholders after execution starts")

    repo.delete_stakeholder(id)
    return None

# --- Preferences ---

@router.post("/decisions/{id}/preferences", response_model=dict, status_code=status.HTTP_201_CREATED)
def add_preference(id: str, payload: PreferenceCreate):
    dec = repo.get_decision(id)
    if not dec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    if dec["status"] not in ["DRAFT", "SETUP"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify preferences after execution starts")

    # Validate stakeholder exists and belongs to this decision
    stk = repo.get_stakeholder(payload.stakeholder_id)
    if not stk or stk["decision_id"] != id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid stakeholder ID")

    if payload.weight <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Preference weight must be positive")
    if payload.priority not in ["high", "medium", "low"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid priority '{payload.priority}'")

    pref_id = repo.add_preference(
        stakeholder_id=payload.stakeholder_id,
        criterion=payload.criterion,
        value=payload.value,
        weight=payload.weight,
        priority=payload.priority,
        description=payload.description
    )
    return {"id": pref_id, "message": "Preference added successfully"}

@router.patch("/preferences/{id}", response_model=dict)
def update_preference(id: str, payload: PreferenceUpdate):
    pref = repo.get_preference(id)
    if not pref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preference not found")

    stk = repo.get_stakeholder(pref["stakeholder_id"])
    dec = repo.get_decision(stk["decision_id"])
    if dec["status"] not in ["DRAFT", "SETUP"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify preferences after execution starts")

    update_data = payload.model_dump(exclude_unset=True)
    if "weight" in update_data and update_data["weight"] <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Preference weight must be positive")
    if "priority" in update_data and update_data["priority"] not in ["high", "medium", "low"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid priority '{update_data['priority']}'")

    repo.update_preference(id, update_data)
    return {"status": "success", "message": "Preference updated successfully"}

@router.delete("/preferences/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_preference(id: str):
    pref = repo.get_preference(id)
    if not pref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preference not found")

    stk = repo.get_stakeholder(pref["stakeholder_id"])
    dec = repo.get_decision(stk["decision_id"])
    if dec["status"] not in ["DRAFT", "SETUP"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify preferences after execution starts")

    repo.delete_preference(id)
    return None

# --- Constraints ---

@router.post("/decisions/{id}/constraints", response_model=dict, status_code=status.HTTP_201_CREATED)
def add_constraint(id: str, payload: ConstraintCreate):
    dec = repo.get_decision(id)
    if not dec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    if dec["status"] not in ["DRAFT", "SETUP"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify constraints after execution starts")

    stk = repo.get_stakeholder(payload.stakeholder_id)
    if not stk or stk["decision_id"] != id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid stakeholder ID")

    if payload.operator not in ["==", "!=", ">", "<", ">=", "<="]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid operator '{payload.operator}'")
    if payload.severity not in ["hard", "soft"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid severity '{payload.severity}'")

    const_id = repo.add_constraint(
        stakeholder_id=payload.stakeholder_id,
        criterion=payload.criterion,
        operator=payload.operator,
        value=payload.value,
        severity=payload.severity
    )
    return {"id": const_id, "message": "Constraint added successfully"}

@router.patch("/constraints/{id}", response_model=dict)
def update_constraint(id: str, payload: ConstraintUpdate):
    const = repo.get_constraint(id)
    if not const:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Constraint not found")

    stk = repo.get_stakeholder(const["stakeholder_id"])
    dec = repo.get_decision(stk["decision_id"])
    if dec["status"] not in ["DRAFT", "SETUP"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify constraints after execution starts")

    update_data = payload.model_dump(exclude_unset=True)
    if "operator" in update_data and update_data["operator"] not in ["==", "!=", ">", "<", ">=", "<="]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid operator '{update_data['operator']}'")
    if "severity" in update_data and update_data["severity"] not in ["hard", "soft"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid severity '{update_data['severity']}'")

    repo.update_constraint(id, update_data)
    return {"status": "success", "message": "Constraint updated successfully"}

@router.delete("/constraints/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_constraint(id: str):
    const = repo.get_constraint(id)
    if not const:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Constraint not found")

    stk = repo.get_stakeholder(const["stakeholder_id"])
    dec = repo.get_decision(stk["decision_id"])
    if dec["status"] not in ["DRAFT", "SETUP"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify constraints after execution starts")

    repo.delete_constraint(id)
    return None

# --- Options ---

@router.post("/decisions/{id}/options", response_model=dict, status_code=status.HTTP_201_CREATED)
def add_option(id: str, payload: DecisionOptionCreate):
    dec = repo.get_decision(id)
    if not dec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    if dec["status"] not in ["DRAFT", "SETUP"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify options after execution starts")

    opt_id = repo.add_option(id, payload.name, payload.description)
    return {"id": opt_id, "message": "Decision option added successfully"}

@router.delete("/options/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_option(id: str):
    opt = repo.get_option(id)
    if not opt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision option not found")

    dec = repo.get_decision(opt["decision_id"])
    if dec["status"] not in ["DRAFT", "SETUP"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify options after execution starts")

    repo.delete_option(id)
    return None

# --- Execution & Approvals ---

@router.post("/decisions/{id}/start", response_model=dict)
async def start_decision(id: str, background_tasks: BackgroundTasks):
    try:
        dec = repo.get_decision(id)
        if not dec:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
            
        current = dec["status"]
        if current == "DRAFT":
            await service.update_status(id, "SETUP")
            current = "SETUP"
        if current == "SETUP":
            await service.update_status(id, "READY")
            
        # Trigger actual agent-based negotiation in background
        negotiation_engine = NegotiationEngine()
        background_tasks.add_task(negotiation_engine.execute_negotiation, id)
        
        return {"status": "success", "message": "Decision negotiation initiated in the background."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/decisions/{id}/status", response_model=dict)
def get_decision_status(id: str):
    dec = repo.get_decision(id)
    if not dec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    return {"id": id, "status": dec["status"], "updated_at": dec["updated_at"]}

@router.get("/decisions/{id}/conflicts", response_model=List[Conflict])
def get_conflicts(id: str):
    return repo.get_conflicts(id)

@router.get("/decisions/{id}/result", response_model=Optional[DecisionOutcome])
def get_decision_result(id: str):
    outcome = repo.get_outcome(id)
    if not outcome:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outcome not available yet")
    return outcome

@router.post("/decisions/{id}/approve", response_model=dict)
async def approve_decision(id: str, payload: ApprovalRequest):
    dec = repo.get_decision(id)
    if not dec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    
    action_state_map = {
        "approve": "APPROVED",
        "reject": "REJECTED",
        "request_changes": "CHANGES_REQUESTED"
    }
    
    next_state = action_state_map.get(payload.action)
    if not next_state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid approval action")
        
    try:
        await service.update_status(id, next_state, authorized_user=payload.stakeholder_id)
        
        # If approved, transition immediately to COMPLETED and save the selected option
        if next_state == "APPROVED":
            await service.update_status(id, "COMPLETED")
            options = dec.get("options", [])
            selected = options[0]["name"] if options else "Option A"
            repo.add_outcome(
                decision_id=id,
                selected_option=selected,
                consensus_score=0.95,
                rationale="Stakeholder approved the consensus outcome.",
                tradeoffs="Approved configuration meets requirements."
            )
            
        return {"status": "success", "message": f"Approval processed, decision status: {dec['status']} -> {next_state}"}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# --- Simulation ---

@router.post("/decisions/{id}/simulate", response_model=dict)
async def simulate_decision(id: str, payload: SimulateRequest):
    try:
        simulated_state = await service.simulate_decision(id, payload.model_dump())
        return simulated_state
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
