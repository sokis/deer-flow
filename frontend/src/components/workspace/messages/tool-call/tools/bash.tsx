"use client";

import { SquareTerminalIcon } from "lucide-react";

import { ChainOfThoughtStep } from "@/components/ai-elements/chain-of-thought";
import { CodeBlock } from "@/components/ai-elements/code-block";

import type { ToolCallProps, ToolCallContext } from "../types";

interface Props extends ToolCallProps, ToolCallContext {
  t: {
    toolCalls: {
      executeCommand: string;
    };
  };
}

export function BashRenderer({ id, args, t }: Props) {
  const description: string | undefined =
    (args.description as string) ?? t.toolCalls.executeCommand;

  if (!description) {
    return (
      <ChainOfThoughtStep
        key={id}
        label={t.toolCalls.executeCommand}
        icon={SquareTerminalIcon}
      />
    );
  }

  const command: string | undefined = (args as { command: string })?.command;

  return (
    <ChainOfThoughtStep key={id} label={description} icon={SquareTerminalIcon}>
      {command && (
        <CodeBlock
          className="mx-0 cursor-pointer border-none px-0"
          showLineNumbers={false}
          language="bash"
          code={command}
        />
      )}
    </ChainOfThoughtStep>
  );
}
