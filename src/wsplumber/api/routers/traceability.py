# src/wsplumber/api/routers/traceability.py
"""
API Router for Tree Verification and Traceability.

Provides endpoints to:
- List available verification trees
- Execute trees against current state
- Get cycle-specific traces
"""

import os
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

router = APIRouter(prefix="/api/traceability", tags=["traceability"])

# Path to tree definitions
TREES_PATH = Path(__file__).parent.parent.parent.parent.parent / "tests" / "scenarios" / "checks"


class TreeNode(BaseModel):
    """Tree node for API response."""
    name: str
    passed: bool
    condition_met: Optional[bool] = None
    message: str = ""
    depth: int = 0
    children: List["TreeNode"] = []


class TreeDefinition(BaseModel):
    """Tree definition summary."""
    name: str
    description: str
    priority: str
    checks_count: int
    file_path: str


class TreeExecutionResult(BaseModel):
    """Result of executing a verification tree."""
    tree_name: str
    total_checks: int
    passed: int
    failed: int
    nodes: List[TreeNode]
    execution_time_ms: float


class CycleTrace(BaseModel):
    """Trace of a single cycle's flow."""
    cycle_id: str
    pair: str
    status: str
    created_at: str
    events: List[Dict[str, Any]]
    checks: List[TreeNode]


@router.get("/trees", response_model=List[TreeDefinition])
async def list_available_trees():
    """List all available verification trees."""
    trees = []
    
    if not TREES_PATH.exists():
        logger.warning(f"Trees path not found: {TREES_PATH}")
        return trees
    
    for yaml_file in TREES_PATH.glob("*.yaml"):
        if yaml_file.name.startswith("_"):
            continue  # Skip schema files
        
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                tree_def = yaml.safe_load(f)
            
            checks = tree_def.get("checks", []) or tree_def.get("tree", [])
            
            trees.append(TreeDefinition(
                name=tree_def.get("scenario", yaml_file.stem),
                description=tree_def.get("description", "No description"),
                priority=tree_def.get("priority", "NORMAL"),
                checks_count=len(checks),
                file_path=str(yaml_file)
            ))
        except Exception as e:
            logger.error(f"Error loading tree {yaml_file}: {e}")
    
    return sorted(trees, key=lambda t: t.priority, reverse=True)


@router.get("/trees/{tree_name}", response_model=Dict[str, Any])
async def get_tree_definition(tree_name: str):
    """Get full tree definition by name."""
    yaml_file = TREES_PATH / f"{tree_name}.yaml"
    
    if not yaml_file.exists():
        raise HTTPException(status_code=404, detail=f"Tree '{tree_name}' not found")
    
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cycles")
async def list_cycles_with_trace():
    """List cycles available for tracing (placeholder - needs orchestrator connection)."""
    # TODO: Connect to repository to get real cycles
    return {
        "cycles": [
            {
                "id": "CYC_EURUSD_001",
                "pair": "EURUSD",
                "status": "ACTIVE",
                "created_at": "2026-01-13T09:00:00Z",
                "operations_count": 4,
                "in_recovery": False
            },
            {
                "id": "CYC_GBPUSD_002",
                "pair": "GBPUSD",
                "status": "HEDGED",
                "created_at": "2026-01-13T08:30:00Z",
                "operations_count": 6,
                "in_recovery": True
            }
        ],
        "total": 2
    }


@router.get("/cycles/{cycle_id}/trace")
async def get_cycle_trace(cycle_id: str):
    """Get detailed trace for a specific cycle."""
    # TODO: Connect to repository and run tree verification
    return {
        "cycle_id": cycle_id,
        "pair": "EURUSD",
        "status": "ACTIVE",
        "trace": [
            {
                "timestamp": "2026-01-13T09:00:00Z",
                "event": "CYCLE_CREATED",
                "details": {"cycle_type": "MAIN", "pair": "EURUSD"},
                "check": {"name": "Cycle Created", "passed": True}
            },
            {
                "timestamp": "2026-01-13T09:00:01Z",
                "event": "OPERATION_CREATED",
                "details": {"op_type": "MAIN_BUY", "entry": 1.0850},
                "check": {"name": "Main Buy Created", "passed": True}
            },
            {
                "timestamp": "2026-01-13T09:00:01Z",
                "event": "OPERATION_CREATED",
                "details": {"op_type": "MAIN_SELL", "entry": 1.0850},
                "check": {"name": "Main Sell Created", "passed": True}
            },
            {
                "timestamp": "2026-01-13T09:15:00Z",
                "event": "OPERATION_ACTIVATED",
                "details": {"op_type": "MAIN_BUY", "price": 1.0852},
                "check": {"name": "Main Activated", "passed": True}
            }
        ],
        "summary": {
            "total_events": 4,
            "checks_passed": 4,
            "checks_failed": 0,
            "current_state": "Waiting for second main activation or TP"
        }
    }


# Update TreeNode to allow self-reference
TreeNode.model_rebuild()
