"use client";

import { MessageCircleQuestionMarkIcon } from "lucide-react";

import { ChainOfThoughtStep } from "@/components/ai-elements/chain-of-thought";

import type { ToolCallProps, ToolCallContext } from "../types";

interface Props extends ToolCallProps, ToolCallContext {
  t: {
    toolCalls: {
      needYourHelp: string;
    };
  };
}

export function AskClarificationRenderer({ id, t }: Props) {
  return (
    <ChainOfThoughtStep
      key={id}
      label={t.toolCalls.needYourHelp}
      icon={MessageCircleQuestionMarkIcon}
    />
  );
}
