"""Rewind router - restore thread state to a previous checkpoint."""
import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.gateway.config import get_gateway_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/threads", tags=["threads"])


class RewindRequest(BaseModel):
    target_turn_index: int


class RewindResponse(BaseModel):
    rewound_to_message_count: int
    filled_text: str


async def _fetch_langgraph_json(client: httpx.AsyncClient, base_url: str, path: str) -> dict:
    response = await client.get(f"{base_url}{path}")
    response.raise_for_status()
    return response.json()


def _human_count(checkpoint: dict) -> int:
    """Count human messages in a checkpoint's messages list."""
    messages = checkpoint.get("values", {}).get("messages", [])
    return sum(1 for m in messages if m.get("type") == "human")


@router.post("/{thread_id}/rewind", response_model=RewindResponse)
async def rewind_thread(thread_id: str, body: RewindRequest) -> RewindResponse:
    """Rewind thread to a previous turn checkpoint.

    Args:
        thread_id: The thread to rewind.
        target_turn_index: The turn index to rewind to. For turn index N, we keep
            messages up to and including turn N, and revert everything after.
            Turn 0 = first human message. Rewinding to turn 0 means discarding
            everything after the first human message.

    Returns:
        rewound_to_message_count: Number of messages after rewind.
        filled_text: The human message text at the rewind point.
    """
    config = get_gateway_config()

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            # Get thread history. LangGraph returns newest-first.
            # Use limit=1000 to get all checkpoints (default pagination is small).
            history = await _fetch_langgraph_json(
                client,
                config.langgraph_internal_url,
                f"/threads/{thread_id}/history?limit=1000",
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Thread not found")
            raise HTTPException(status_code=502, detail="LangGraph error") from exc
        except httpx.HTTPError as exc:
            logger.exception("LangGraph history fetch failed: thread_id=%s", thread_id)
            raise HTTPException(status_code=502, detail="LangGraph unavailable") from exc

    if not history or not isinstance(history, list):
        raise HTTPException(status_code=404, detail="Thread has no history")

    target_idx = body.target_turn_index
    if target_idx < 0:
        raise HTTPException(status_code=400, detail="target_turn_index must be >= 0")

    # history is newest-first; reverse to oldest-first for chronological traversal
    oldest_first = list(reversed(history))

    # "Rewind to turn N" = restore to the oldest checkpoint where human_count > N.
    # This is the checkpoint that existed JUST BEFORE turn N+1 started,
    # meaning messages up to and including turn N are preserved.
    target_checkpoint = None
    for cp in oldest_first:
        if _human_count(cp) > target_idx:
            target_checkpoint = cp
            break

    if target_checkpoint is None:
        raise HTTPException(
            status_code=404,
            detail=f"Turn index {target_idx} out of range (max: {_human_count(oldest_first[-1]) - 1})"
        )

    # Fork from the target checkpoint to restore server-side state.
    # POST /threads/{tid}/state with checkpoint_id and empty values creates a new
    # checkpoint branch from the target, effectively rewinding the thread state.
    target_checkpoint_id = target_checkpoint.get("checkpoint_id") or target_checkpoint.get("id")
    if not target_checkpoint_id:
        raise HTTPException(status_code=500, detail="Checkpoint has no ID")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            fork_resp = await client.post(
                f"{config.langgraph_internal_url}/threads/{thread_id}/state",
                json={
                    "values": {},  # Empty values = fork without merging new content
                    "checkpoint_id": target_checkpoint_id,
                },
            )
            if fork_resp.status_code not in (200, 201):
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to restore checkpoint: {fork_resp.status_code}",
                )
    except httpx.HTTPError as exc:
        logger.exception("LangGraph state update failed: thread_id=%s", thread_id)
        raise HTTPException(status_code=502, detail="LangGraph unavailable") from exc

    # Extract filled_text: the human message at the rewind point
    # values.messages is the list of messages in this checkpoint
    values = target_checkpoint.get("values", {})
    messages = values.get("messages", [])

    filled_text = ""
    for msg in reversed(messages):
        msg_type = msg.get("type", "")
        if msg_type == "human":
            content = msg.get("content", "")
            if isinstance(content, str):
                filled_text = content
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        filled_text = block.get("text", "")
                        break
            break

    return RewindResponse(
        rewound_to_message_count=len(messages),
        filled_text=filled_text,
    )
