import logging
from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.gateway.config import get_gateway_config
from deerflow.config.paths import Paths, get_paths

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/threads", tags=["threads"])

# Stuck detection thresholds (in seconds)
STUCK_THRESHOLD_DEFAULT = 120  # 2 minutes without progress = suspected stuck
STUCK_THRESHOLD_LONG = 300  # 5 minutes = confirmed stuck
PROGRESS_CHECK_INTERVAL = 10  # Check every 10 seconds of idle time

# Mapping from LangGraph run statuses to truth_phase
RUN_STATUS_TO_TRUTH_PHASE = {
    "success": "completed",
    "failed": "error",
    "stopped": "interrupted",
    "cancelled": "interrupted",
}


def _map_run_status_to_truth_phase(status: str | None) -> str:
    """Map LangGraph run status to truth_phase."""
    if status is None:
        return "idle"
    # Check for exact match first
    if status in RUN_STATUS_TO_TRUTH_PHASE:
        return RUN_STATUS_TO_TRUTH_PHASE[status]
    # Handle other statuses
    status_lower = status.lower()
    if "run" in status_lower or "execut" in status_lower:
        return "running"
    if "wait" in status_lower:
        return "waiting"
    if "interrupt" in status_lower:
        return "interrupted"
    return "idle"


async def _fetch_langgraph_json(client: httpx.AsyncClient, base_url: str, path: str) -> dict:
    """Fetch JSON from LangGraph API."""
    response = await client.get(f"{base_url}{path}")
    response.raise_for_status()
    return response.json()


class ThreadRunHealthResponse(BaseModel):
    """Response model for thread run health endpoint."""

    thread_id: str
    run_id: str | None
    status_raw: str | None
    truth_phase: str
    reason_code: str
    created_at: str | None
    updated_at: str | None
    last_progress_at: str | None
    last_progress_source: str | None
    checkpoint_created_at: str | None
    idle_seconds: int | None
    message_count: int
    next_nodes: list[str]
    # Stuck detection fields
    is_stuck: bool = False
    stuck_reason: str | None = None
    last_message_at: str | None = None
    model_name: str | None = None


class ThreadDeleteResponse(BaseModel):
    """Response model for thread cleanup."""

    success: bool
    message: str


def _delete_thread_data(thread_id: str, paths: Paths | None = None) -> ThreadDeleteResponse:
    """Delete local persisted filesystem data for a thread."""
    path_manager = paths or get_paths()
    try:
        path_manager.delete_thread_dir(thread_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to delete thread data for %s", thread_id)
        raise HTTPException(status_code=500, detail="Failed to delete local thread data.") from exc

    logger.info("Deleted local thread data for %s", thread_id)
    return ThreadDeleteResponse(success=True, message=f"Deleted local thread data for {thread_id}")


@router.delete("/{thread_id}", response_model=ThreadDeleteResponse)
async def delete_thread_data(thread_id: str) -> ThreadDeleteResponse:
    """Delete local persisted filesystem data for a thread.

    This endpoint only cleans DeerFlow-managed thread directories. LangGraph
    thread state deletion remains handled by the LangGraph API.
    """
    return _delete_thread_data(thread_id)


@router.get("/{thread_id}/run-health", response_model=ThreadRunHealthResponse)
async def get_thread_run_health(
    thread_id: str,
    stuck_threshold: Annotated[int, Query(description="Seconds to consider run as stuck", ge=30, le=600)] = STUCK_THRESHOLD_DEFAULT,
) -> ThreadRunHealthResponse:
    """Get the run health status for a thread.

    This endpoint queries LangGraph to determine the current run status of a thread
    and maps it to the frontend's truth_phase system.

    Includes STUCK DETECTION:
    - If run is 'running' for longer than stuck_threshold seconds without message count change -> stuck
    - If run is 'waiting' for longer than stuck_threshold seconds -> stuck
    - Reports stuck_reason to help diagnose the issue

    Returns:
        ThreadRunHealthResponse with current run status, metadata, and stuck detection.
    """
    config = get_gateway_config()

    now = datetime.now(UTC)
    run_id: str | None = None
    status_raw: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    last_progress_at: str | None = None
    last_progress_source: str | None = None
    checkpoint_created_at: str | None = None
    message_count = 0
    next_nodes: list[str] = []
    idle_seconds: int | None = None
    reason_code = ""
    is_stuck = False
    stuck_reason: str | None = None
    last_message_at: str | None = None
    model_name: str | None = None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get run history from LangGraph
            try:
                runs_response = await _fetch_langgraph_json(
                    client,
                    config.langgraph_internal_url,
                    f"/threads/{thread_id}/runs?limit=5",  # Fetch more runs for analysis
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    # Thread not found - return idle
                    return ThreadRunHealthResponse(
                        thread_id=thread_id,
                        run_id=None,
                        status_raw=None,
                        truth_phase="idle",
                        reason_code="thread_not_found",
                        created_at=None,
                        updated_at=None,
                        last_progress_at=None,
                        last_progress_source=None,
                        checkpoint_created_at=None,
                        idle_seconds=None,
                        message_count=0,
                        next_nodes=[],
                        is_stuck=False,
                        stuck_reason=None,
                        last_message_at=None,
                        model_name=None,
                    )
                raise HTTPException(status_code=502, detail="LangGraph error") from exc
            except httpx.HTTPError as exc:
                logger.exception("LangGraph runs fetch failed: thread_id=%s", thread_id)
                raise HTTPException(status_code=502, detail="LangGraph unavailable") from exc

            # Extract runs list - LangGraph may return {"runs": [...]} or direct [...]
            if isinstance(runs_response, list):
                runs = runs_response
            elif isinstance(runs_response, dict):
                runs = runs_response.get("runs", [])
            else:
                runs = []

            # Get current state to count messages
            try:
                state_response = await _fetch_langgraph_json(
                    client,
                    config.langgraph_internal_url,
                    f"/threads/{thread_id}/state",
                )
                # Extract message count and metadata from state
                if isinstance(state_response, dict):
                    values = state_response.get("values", {})
                    if isinstance(values, dict):
                        messages = values.get("messages", [])
                        message_count = len(messages) if isinstance(messages, list) else 0
                        # Extract model_name from configurable if present
                        configurable = state_response.get("configurable", {})
                        model_name = configurable.get("model_name") if isinstance(configurable, dict) else None
                        # Try to get last message time
                        if isinstance(messages, list) and messages:
                            last_msg = messages[-1]
                            if isinstance(last_msg, dict):
                                last_message_at = last_msg.get("created_at")
                    # Extract next nodes from state
                    next_nodes = state_response.get("next_nodes", [])
                    if not isinstance(next_nodes, list):
                        next_nodes = []
            except Exception:
                # If state fetch fails, continue without message count
                pass

            if not runs:
                # No runs - thread is idle
                truth_phase = "idle"
                reason_code = "no_active_runs"
                idle_seconds = 0
            else:
                # Get the most recent run (runs are newest-first)
                latest_run = runs[0] if runs else {}
                run_id = latest_run.get("run_id")
                status_raw = latest_run.get("status")
                created_at = latest_run.get("created_at")
                updated_at = latest_run.get("updated_at")

                # Map status to truth_phase
                truth_phase = _map_run_status_to_truth_phase(status_raw)

                # Calculate idle time and check for stuck
                if truth_phase in ("completed", "error", "interrupted"):
                    if created_at:
                        try:
                            run_created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                            idle_seconds = int((now - run_created).total_seconds())
                        except Exception:
                            idle_seconds = None
                    reason_code = f"run_{truth_phase}"
                elif truth_phase in ("running", "waiting"):
                    # Check if run is stuck
                    if created_at:
                        try:
                            run_created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                            running_seconds = int((now - run_created).total_seconds())
                        except Exception:
                            running_seconds = 0

                        # Stuck detection logic
                        if running_seconds >= stuck_threshold:
                            # Run has been running/waiting for too long
                            is_stuck = True
                            if truth_phase == "waiting":
                                stuck_reason = f"waiting_for_response_{running_seconds}s"
                                reason_code = "stuck_waiting"
                            else:
                                stuck_reason = f"no_progress_{running_seconds}s"
                                reason_code = "stuck_running"
                            truth_phase = "stuck"
                            idle_seconds = running_seconds
                            logger.warning(
                                "[STUCK DETECTED] thread_id=%s run_id=%s status=%s running_seconds=%d message_count=%d",
                                thread_id, run_id, status_raw, running_seconds, message_count,
                            )
                        else:
                            reason_code = f"run_{truth_phase}"
                            idle_seconds = running_seconds
                    else:
                        reason_code = f"run_{truth_phase}"
                else:
                    reason_code = f"run_{truth_phase}"

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error in get_thread_run_health: thread_id=%s", thread_id)
        raise HTTPException(status_code=500, detail="Internal error") from exc

    return ThreadRunHealthResponse(
        thread_id=thread_id,
        run_id=run_id,
        status_raw=status_raw,
        truth_phase=truth_phase,
        reason_code=reason_code,
        created_at=created_at,
        updated_at=updated_at,
        last_progress_at=last_progress_at,
        last_progress_source=last_progress_source,
        checkpoint_created_at=checkpoint_created_at,
        idle_seconds=idle_seconds,
        message_count=message_count,
        next_nodes=next_nodes,
        is_stuck=is_stuck,
        stuck_reason=stuck_reason,
        last_message_at=last_message_at,
        model_name=model_name,
    )
