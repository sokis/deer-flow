"use client";

import { WrenchIcon } from "lucide-react";

import { ChainOfThoughtStep } from "@/components/ai-elements/chain-of-thought";

import type { ToolCallProps, ToolCallContext } from "../types";

interface Props extends ToolCallProps, ToolCallContext {
  t: {
    toolCalls: {
      useTool: (name: string) => string;
    };
  };
}

export function DefaultRenderer({ id, name, args, t }: Props) {
  const description: string | undefined =
    (args.description as string) ?? t.toolCalls.useTool(name);

  return (
    <ChainOfThoughtStep
      key={id}
      label={description ?? t.toolCalls.useTool(name)}
      icon={WrenchIcon}
    />
  );
}
