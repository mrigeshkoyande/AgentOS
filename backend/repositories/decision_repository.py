import sqlite3
import os
import uuid
import json
from datetime import datetime
from typing import List, Dict, Optional

DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agentos.db"))

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def create_tables():
    conn = get_db()
    cursor = conn.cursor()
    
    # decisions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decisions (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'DRAFT',
        strategy TEXT DEFAULT 'consensus',
        deadline TEXT,
        consensus_threshold REAL DEFAULT 0.7,
        max_rounds INTEGER DEFAULT 5,
        compromise_allowed BOOLEAN DEFAULT 1,
        approval_required BOOLEAN DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    )
    """)
    
    # stakeholders
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stakeholders (
        id TEXT PRIMARY KEY,
        decision_id TEXT NOT NULL,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        type TEXT,
        weight REAL DEFAULT 1.0,
        approval_required BOOLEAN DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (decision_id) REFERENCES decisions(id) ON DELETE CASCADE
    )
    """)
    
    # preferences
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS preferences (
        id TEXT PRIMARY KEY,
        stakeholder_id TEXT NOT NULL,
        criterion TEXT NOT NULL,
        value TEXT NOT NULL,
        weight REAL DEFAULT 1.0,
        priority TEXT DEFAULT 'medium',
        description TEXT,
        FOREIGN KEY (stakeholder_id) REFERENCES stakeholders(id) ON DELETE CASCADE
    )
    """)
    
    # constraints
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS constraints (
        id TEXT PRIMARY KEY,
        stakeholder_id TEXT NOT NULL,
        criterion TEXT NOT NULL,
        operator TEXT NOT NULL,
        value TEXT NOT NULL,
        severity TEXT DEFAULT 'soft',
        FOREIGN KEY (stakeholder_id) REFERENCES stakeholders(id) ON DELETE CASCADE
    )
    """)
    
    # decision_options
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decision_options (
        id TEXT PRIMARY KEY,
        decision_id TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        FOREIGN KEY (decision_id) REFERENCES decisions(id) ON DELETE CASCADE
    )
    """)
    
    # conflicts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conflicts (
        id TEXT PRIMARY KEY,
        decision_id TEXT NOT NULL,
        criterion TEXT NOT NULL,
        stakeholder_ids TEXT NOT NULL,
        description TEXT NOT NULL,
        severity TEXT DEFAULT 'medium',
        status TEXT DEFAULT 'active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        resolved_at TEXT,
        FOREIGN KEY (decision_id) REFERENCES decisions(id) ON DELETE CASCADE
    )
    """)
    
    # negotiation_rounds
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS negotiation_rounds (
        id TEXT PRIMARY KEY,
        decision_id TEXT NOT NULL,
        round_number INTEGER NOT NULL,
        status TEXT DEFAULT 'active',
        proposal TEXT,
        counter_proposal TEXT,
        reason TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT,
        FOREIGN KEY (decision_id) REFERENCES decisions(id) ON DELETE CASCADE
    )
    """)
    
    # decision_votes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decision_votes (
        id TEXT PRIMARY KEY,
        decision_id TEXT NOT NULL,
        stakeholder_id TEXT NOT NULL,
        option_id TEXT NOT NULL,
        score REAL NOT NULL,
        reason TEXT,
        FOREIGN KEY (decision_id) REFERENCES decisions(id) ON DELETE CASCADE,
        FOREIGN KEY (stakeholder_id) REFERENCES stakeholders(id) ON DELETE CASCADE,
        FOREIGN KEY (option_id) REFERENCES decision_options(id) ON DELETE CASCADE
    )
    """)
    
    # decision_outcomes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decision_outcomes (
        id TEXT PRIMARY KEY,
        decision_id TEXT NOT NULL,
        selected_option TEXT NOT NULL,
        consensus_score REAL NOT NULL,
        rationale TEXT NOT NULL,
        tradeoffs TEXT,
        dissent TEXT,
        next_actions TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (decision_id) REFERENCES decisions(id) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    conn.close()

class DecisionRepository:
    def __init__(self):
        create_tables()
        
    def create_decision(self, session_id: str, title: str, description: Optional[str] = None, 
                        strategy: str = "consensus", deadline: Optional[str] = None, 
                        consensus_threshold: float = 0.7, max_rounds: int = 5, 
                        compromise_allowed: bool = True, approval_required: bool = True) -> str:
        conn = get_db()
        cursor = conn.cursor()
        decision_id = f"dec_{uuid.uuid4().hex[:10]}"
        cursor.execute(
            """INSERT INTO decisions 
               (id, session_id, title, description, status, strategy, deadline, consensus_threshold, max_rounds, compromise_allowed, approval_required) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (decision_id, session_id, title, description, "DRAFT", strategy, deadline, consensus_threshold, max_rounds, int(compromise_allowed), int(approval_required))
        )
        conn.commit()
        conn.close()
        return decision_id

    def get_decision(self, decision_id: str) -> Optional[dict]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        dec = dict(row)
        # Convert sqlite ints to booleans
        dec["compromise_allowed"] = bool(dec["compromise_allowed"])
        dec["approval_required"] = bool(dec["approval_required"])
        
        # Load nested objects
        cursor.execute("SELECT * FROM stakeholders WHERE decision_id = ?", (decision_id,))
        dec["stakeholders"] = [dict(r) for r in cursor.fetchall()]
        for stk in dec["stakeholders"]:
            stk["approval_required"] = bool(stk["approval_required"])
            
        cursor.execute("SELECT * FROM preferences WHERE stakeholder_id IN (SELECT id FROM stakeholders WHERE decision_id = ?)", (decision_id,))
        dec["preferences"] = [dict(r) for r in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM constraints WHERE stakeholder_id IN (SELECT id FROM stakeholders WHERE decision_id = ?)", (decision_id,))
        dec["constraints"] = [dict(r) for r in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM decision_options WHERE decision_id = ?", (decision_id,))
        dec["options"] = [dict(r) for r in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM conflicts WHERE decision_id = ?", (decision_id,))
        dec["conflicts"] = []
        for r in cursor.fetchall():
            c = dict(r)
            c["stakeholder_ids"] = json.loads(c["stakeholder_ids"])
            dec["conflicts"].append(c)
            
        cursor.execute("SELECT * FROM negotiation_rounds WHERE decision_id = ? ORDER BY round_number ASC", (decision_id,))
        dec["negotiation_rounds"] = [dict(r) for r in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM decision_votes WHERE decision_id = ?", (decision_id,))
        dec["votes"] = [dict(r) for r in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM decision_outcomes WHERE decision_id = ?", (decision_id,))
        out_row = cursor.fetchone()
        dec["outcome"] = dict(out_row) if out_row else None
        
        conn.close()
        return dec

    def update_decision(self, decision_id: str, fields: dict) -> bool:
        if not fields:
            return False
        conn = get_db()
        cursor = conn.cursor()
        
        # Ensure updated_at is updated
        fields["updated_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        # Handle datetime updates
        if "status" in fields and fields["status"] in ["APPROVED", "COMPLETED", "FAILED", "REJECTED"]:
            fields["completed_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        keys = []
        values = []
        for k, v in fields.items():
            keys.append(f"{k} = ?")
            if isinstance(v, bool):
                values.append(int(v))
            else:
                values.append(v)
        
        values.append(decision_id)
        query = f"UPDATE decisions SET {', '.join(keys)} WHERE id = ?"
        cursor.execute(query, tuple(values))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def delete_decision(self, decision_id: str) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM decisions WHERE id = ?", (decision_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    # Stakeholders
    def add_stakeholder(self, decision_id: str, name: str, role: str, 
                        stk_type: Optional[str] = None, weight: float = 1.0, 
                        approval_required: bool = False) -> str:
        conn = get_db()
        cursor = conn.cursor()
        stk_id = f"stk_{uuid.uuid4().hex[:10]}"
        cursor.execute(
            """INSERT INTO stakeholders (id, decision_id, name, role, type, weight, approval_required) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (stk_id, decision_id, name, role, stk_type, weight, int(approval_required))
        )
        conn.commit()
        conn.close()
        return stk_id

    def get_stakeholder(self, stakeholder_id: str) -> Optional[dict]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM stakeholders WHERE id = ?", (stakeholder_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_stakeholder(self, stakeholder_id: str, fields: dict) -> bool:
        if not fields:
            return False
        conn = get_db()
        cursor = conn.cursor()
        keys = []
        values = []
        for k, v in fields.items():
            keys.append(f"{k} = ?")
            if isinstance(v, bool):
                values.append(int(v))
            else:
                values.append(v)
        values.append(stakeholder_id)
        query = f"UPDATE stakeholders SET {', '.join(keys)} WHERE id = ?"
        cursor.execute(query, tuple(values))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def delete_stakeholder(self, stakeholder_id: str) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM stakeholders WHERE id = ?", (stakeholder_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    # Preferences
    def add_preference(self, stakeholder_id: str, criterion: str, value: str, 
                       weight: float = 1.0, priority: str = "medium", 
                       description: Optional[str] = None) -> str:
        conn = get_db()
        cursor = conn.cursor()
        pref_id = f"pref_{uuid.uuid4().hex[:10]}"
        cursor.execute(
            """INSERT INTO preferences (id, stakeholder_id, criterion, value, weight, priority, description) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (pref_id, stakeholder_id, criterion, value, weight, priority, description)
        )
        conn.commit()
        conn.close()
        return pref_id

    def get_preference(self, preference_id: str) -> Optional[dict]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM preferences WHERE id = ?", (preference_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_preference(self, preference_id: str, fields: dict) -> bool:
        if not fields:
            return False
        conn = get_db()
        cursor = conn.cursor()
        keys = []
        values = []
        for k, v in fields.items():
            keys.append(f"{k} = ?")
            values.append(v)
        values.append(preference_id)
        query = f"UPDATE preferences SET {', '.join(keys)} WHERE id = ?"
        cursor.execute(query, tuple(values))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def delete_preference(self, preference_id: str) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM preferences WHERE id = ?", (preference_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    # Constraints
    def add_constraint(self, stakeholder_id: str, criterion: str, operator: str, 
                       value: str, severity: str = "soft") -> str:
        conn = get_db()
        cursor = conn.cursor()
        const_id = f"const_{uuid.uuid4().hex[:10]}"
        cursor.execute(
            """INSERT INTO constraints (id, stakeholder_id, criterion, operator, value, severity) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (const_id, stakeholder_id, criterion, operator, value, severity)
        )
        conn.commit()
        conn.close()
        return const_id

    def get_constraint(self, constraint_id: str) -> Optional[dict]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM constraints WHERE id = ?", (constraint_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_constraint(self, constraint_id: str, fields: dict) -> bool:
        if not fields:
            return False
        conn = get_db()
        cursor = conn.cursor()
        keys = []
        values = []
        for k, v in fields.items():
            keys.append(f"{k} = ?")
            values.append(v)
        values.append(constraint_id)
        query = f"UPDATE constraints SET {', '.join(keys)} WHERE id = ?"
        cursor.execute(query, tuple(values))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def delete_constraint(self, constraint_id: str) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM constraints WHERE id = ?", (constraint_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    # Options
    def add_option(self, decision_id: str, name: str, description: Optional[str] = None) -> str:
        conn = get_db()
        cursor = conn.cursor()
        opt_id = f"opt_{uuid.uuid4().hex[:10]}"
        cursor.execute(
            "INSERT INTO decision_options (id, decision_id, name, description) VALUES (?, ?, ?, ?)",
            (opt_id, decision_id, name, description)
        )
        conn.commit()
        conn.close()
        return opt_id

    def get_option(self, option_id: str) -> Optional[dict]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM decision_options WHERE id = ?", (option_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def delete_option(self, option_id: str) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM decision_options WHERE id = ?", (option_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    # Conflicts
    def add_conflict(self, decision_id: str, criterion: str, stakeholder_ids: List[str], 
                     description: str, severity: str = "medium") -> str:
        conn = get_db()
        cursor = conn.cursor()
        conflict_id = f"conf_{uuid.uuid4().hex[:10]}"
        cursor.execute(
            """INSERT INTO conflicts (id, decision_id, criterion, stakeholder_ids, description, severity, status) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (conflict_id, decision_id, criterion, json.dumps(stakeholder_ids), description, severity, "active")
        )
        conn.commit()
        conn.close()
        return conflict_id

    def get_conflicts(self, decision_id: str) -> List[dict]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conflicts WHERE decision_id = ?", (decision_id,))
        conflicts = []
        for r in cursor.fetchall():
            c = dict(r)
            c["stakeholder_ids"] = json.loads(c["stakeholder_ids"])
            conflicts.append(c)
        conn.close()
        return conflicts

    def resolve_conflict(self, conflict_id: str) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        resolved_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "UPDATE conflicts SET status = 'resolved', resolved_at = ? WHERE id = ?",
            (resolved_at, conflict_id)
        )
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    # Negotiation Rounds
    def add_negotiation_round(self, decision_id: str, round_number: int, proposal: str, 
                              counter_proposal: Optional[str] = None, reason: Optional[str] = None) -> str:
        conn = get_db()
        cursor = conn.cursor()
        round_id = f"neg_{uuid.uuid4().hex[:10]}"
        cursor.execute(
            """INSERT INTO negotiation_rounds (id, decision_id, round_number, status, proposal, counter_proposal, reason) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (round_id, decision_id, round_number, "active", proposal, counter_proposal, reason)
        )
        conn.commit()
        conn.close()
        return round_id

    def update_negotiation_round(self, round_id: str, fields: dict) -> bool:
        if not fields:
            return False
        conn = get_db()
        cursor = conn.cursor()
        
        if "status" in fields and fields["status"] == "completed":
            fields["completed_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            
        keys = []
        values = []
        for k, v in fields.items():
            keys.append(f"{k} = ?")
            values.append(v)
        values.append(round_id)
        query = f"UPDATE negotiation_rounds SET {', '.join(keys)} WHERE id = ?"
        cursor.execute(query, tuple(values))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    # Votes
    def add_vote(self, decision_id: str, stakeholder_id: str, option_id: str, 
                 score: float, reason: Optional[str] = None) -> str:
        conn = get_db()
        cursor = conn.cursor()
        vote_id = f"vote_{uuid.uuid4().hex[:10]}"
        cursor.execute(
            """INSERT INTO decision_votes (id, decision_id, stakeholder_id, option_id, score, reason) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (vote_id, decision_id, stakeholder_id, option_id, score, reason)
        )
        conn.commit()
        conn.close()
        return vote_id

    # Outcomes
    def add_outcome(self, decision_id: str, selected_option: str, consensus_score: float, 
                    rationale: str, tradeoffs: Optional[str] = None, dissent: Optional[str] = None, 
                    next_actions: Optional[str] = None) -> str:
        conn = get_db()
        cursor = conn.cursor()
        outcome_id = f"out_{uuid.uuid4().hex[:10]}"
        cursor.execute(
            """INSERT INTO decision_outcomes (id, decision_id, selected_option, consensus_score, rationale, tradeoffs, dissent, next_actions) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (outcome_id, decision_id, selected_option, consensus_score, rationale, tradeoffs, dissent, next_actions)
        )
        conn.commit()
        conn.close()
        return outcome_id

    def get_outcome(self, decision_id: str) -> Optional[dict]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM decision_outcomes WHERE decision_id = ?", (decision_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    # History
    def get_history(self) -> List[dict]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM decisions ORDER BY created_at DESC")
        decisions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return decisions
