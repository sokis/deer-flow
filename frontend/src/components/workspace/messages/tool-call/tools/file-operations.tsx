"use client";

import { BookOpenTextIcon, FolderOpenIcon, NotebookPenIcon } from "lucide-react";

import {
  ChainOfThoughtSearchResult,
  ChainOfThoughtStep,
} from "@/components/ai-elements/chain-of-thought";

import type { ToolCallProps, ToolCallContext } from "../types";

interface Props extends ToolCallProps, ToolCallContext {
  t: {
    toolCalls: {
      listFolder: string;
      readFile: string;
      writeFile: string;
      executeCommand: string;
    };
  };
}

export function FileOperationsRenderer({
  id,
  name,
  args,
  isLast,
  isLoading,
  messageId,
  t,
  setOpen,
  autoOpen,
  autoSelect,
  selectedArtifact,
  select,
}: Props) {
  const path: string | undefined = (args as { path: string })?.path;

  if (name === "ls") {
    const description: string | undefined =
      (args.description as string) ?? t.toolCalls.listFolder;
    return (
      <ChainOfThoughtStep key={id} label={description} icon={FolderOpenIcon}>
        {path && (
          <ChainOfThoughtSearchResult className="cursor-pointer">
            {path}
          </ChainOfThoughtSearchResult>
        )}
      </ChainOfThoughtStep>
    );
  }

  if (name === "read_file") {
    const description: string | undefined =
      (args.description as string) ?? t.toolCalls.readFile;
    return (
      <ChainOfThoughtStep key={id} label={description} icon={BookOpenTextIcon}>
        {path && (
          <ChainOfThoughtSearchResult className="cursor-pointer">
            {path}
          </ChainOfThoughtSearchResult>
        )}
      </ChainOfThoughtStep>
    );
  }

  // write_file or str_replace
  const description: string | undefined =
    (args.description as string) ?? t.toolCalls.writeFile;

  if (isLoading && isLast && autoOpen && autoSelect && path) {
    setTimeout(() => {
      const url = new URL(
        `write-file:${path}?message_id=${messageId}&tool_call_id=${id}`,
      ).toString();
      if (selectedArtifact === url) {
        return;
      }
      select(url, true);
      setOpen(true);
    }, 100);
  }

  return (
    <ChainOfThoughtStep
      key={id}
      className="cursor-pointer"
      label={description}
      icon={NotebookPenIcon}
      onClick={() => {
        select(
          new URL(
            `write-file:${path}?message_id=${messageId}&tool_call_id=${id}`,
          ).toString(),
        );
        setOpen(true);
      }}
    >
      {path && (
        <ChainOfThoughtSearchResult className="cursor-pointer">
          {path}
        </ChainOfThoughtSearchResult>
      )}
    </ChainOfThoughtStep>
  );
}
