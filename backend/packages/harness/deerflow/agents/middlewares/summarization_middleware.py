"""Custom summarization middleware that handles dict messages.

This module provides a SafeSummarizationMiddleware that extends LangChain's
SummarizationMiddleware to handle cases where messages may be dict objects
instead of proper message class instances (e.g., after checkpoint serialization).
"""

from __future__ import annotations

import uuid

from langchain.agents.middleware import SummarizationMiddleware as LangChainSummarizationMiddleware
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage


class SafeSummarizationMiddleware(LangChainSummarizationMiddleware):
    """A safe version of SummarizationMiddleware that handles dict messages.

    LangChain's SummarizationMiddleware._ensure_message_ids assumes all messages
    have a .id attribute, but when messages are retrieved from a checkpoint
    (especially after serialization/deserialization), they may be dict objects
    that don't have this attribute.

    This subclass converts dict messages to proper message objects before
    calling the parent's _ensure_message_ids method.
    """

    def _ensure_message_ids(self, messages: list[AnyMessage]) -> None:
        """Ensure all messages have unique IDs, handling both dict and message objects."""
        converted_messages: list[AnyMessage] = []
        for msg in messages:
            if isinstance(msg, dict):
                # Convert dict to appropriate message type
                msg = self._dict_to_message(msg)
            converted_messages.append(msg)

        # Call parent method with converted messages
        self._ensure_message_ids_safe(converted_messages)

    def _ensure_message_ids_safe(self, messages: list[AnyMessage]) -> None:
        """Original _ensure_message_ids implementation from parent class."""
        for msg in messages:
            if msg.id is None:
                msg.id = str(uuid.uuid4())

    @staticmethod
    def _dict_to_message(msg_dict: dict) -> AnyMessage:
        """Convert a dict to the appropriate message type."""
        msg_type = msg_dict.get("type", "")

        if msg_type == "ai":
            content = msg_dict.get("content", "")
            additional_kwargs = msg_dict.get("additional_kwargs", {})
            response_metadata = msg_dict.get("response_metadata", {})
            id_ = msg_dict.get("id")
            tool_calls = msg_dict.get("tool_calls")
            invalid_tool_calls = msg_dict.get("invalid_tool_calls")

            return AIMessage(
                content=content,
                additional_kwargs=additional_kwargs,
                response_metadata=response_metadata,
                id=id_,
                tool_calls=tool_calls,
                invalid_tool_calls=invalid_tool_calls,
            )
        elif msg_type == "human":
            content = msg_dict.get("content", "")
            additional_kwargs = msg_dict.get("additional_kwargs", {})
            id_ = msg_dict.get("id")
            name = msg_dict.get("name")

            return HumanMessage(
                content=content,
                additional_kwargs=additional_kwargs,
                id=id_,
                name=name,
            )
        elif msg_type == "tool":
            content = msg_dict.get("content", "")
            tool_call_id = msg_dict.get("tool_call_id")
            name = msg_dict.get("name")
            id_ = msg_dict.get("id")
            additional_kwargs = msg_dict.get("additional_kwargs", {})

            return ToolMessage(
                content=content,
                tool_call_id=tool_call_id,
                name=name,
                id=id_,
                additional_kwargs=additional_kwargs,
            )
        else:
            # Fallback: try to create a generic message
            # Use content as string or serialize the dict
            content = msg_dict.get("content", str(msg_dict))
            return HumanMessage(content=content)
