import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.gateway.config import get_gateway_config
from deerflow.config.paths import Paths, get_paths

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/threads", tags=["threads"])

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
async def get_thread_run_health(thread_id: str) -> ThreadRunHealthResponse:
    """Get the run health status for a thread.

    This endpoint queries LangGraph to determine the current run status of a thread
    and maps it to the frontend's truth_phase system.

    Returns:
        ThreadRunHealthResponse with current run status and metadata.
    """
    config = get_gateway_config()

    now = datetime.now(timezone.utc)
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

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get run history from LangGraph
            try:
                runs_response = await _fetch_langgraph_json(
                    client,
                    config.langgraph_internal_url,
                    f"/threads/{thread_id}/runs?limit=1",
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
                    )
                raise HTTPException(status_code=502, detail="LangGraph error") from exc
            except httpx.HTTPError as exc:
                logger.exception("LangGraph runs fetch failed: thread_id=%s", thread_id)
                raise HTTPException(status_code=502, detail="LangGraph unavailable") from exc

            # Extract runs list - LangGraph returns {"runs": [...]}
            runs = runs_response.get("runs", []) if isinstance(runs_response, dict) else []

            # Get current state to count messages
            try:
                state_response = await _fetch_langgraph_json(
                    client,
                    config.langgraph_internal_url,
                    f"/threads/{thread_id}/state",
                )
                # Extract message count from state
                values = state_response.get("values", {}) if isinstance(state_response, dict) else {}
                messages = values.get("messages", []) if isinstance(values, dict) else []
                message_count = len(messages) if isinstance(messages, list) else 0
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

                # Map status to truth_phase
                truth_phase = _map_run_status_to_truth_phase(status_raw)

                # Calculate idle time if the run is completed
                if truth_phase in ("completed", "error", "interrupted"):
                    if created_at:
                        try:
                            run_created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                            idle_seconds = int((now - run_created).total_seconds())
                        except Exception:
                            idle_seconds = None
                    reason_code = f"run_{truth_phase}"
                else:
                    reason_code = f"run_{truth_phase}"
                    idle_seconds = None

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
    )
