"use client";

import { ListTodoIcon } from "lucide-react";

import { ChainOfThoughtStep } from "@/components/ai-elements/chain-of-thought";

import type { ToolCallProps, ToolCallContext } from "../types";

interface Props extends ToolCallProps, ToolCallContext {
  t: {
    toolCalls: {
      writeTodos: string;
    };
  };
}

export function WriteTodosRenderer({ id, t }: Props) {
  return (
    <ChainOfThoughtStep
      key={id}
      label={t.toolCalls.writeTodos}
      icon={ListTodoIcon}
    />
  );
}
