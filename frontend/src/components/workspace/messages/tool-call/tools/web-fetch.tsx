"use client";

import { GlobeIcon } from "lucide-react";

import {
  ChainOfThoughtSearchResult,
  ChainOfThoughtStep,
} from "@/components/ai-elements/chain-of-thought";
import { extractTitleFromMarkdown } from "@/core/utils/markdown";

import type { ToolCallProps, ToolCallContext } from "../types";

interface Props extends ToolCallProps, ToolCallContext {
  t: {
    toolCalls: {
      viewWebPage: string;
    };
  };
}

export function WebFetchRenderer({ id, args, result, t }: Props) {
  const url = (args as { url: string })?.url;
  let title = url;

  if (typeof result === "string") {
    const potentialTitle = extractTitleFromMarkdown(result);
    if (potentialTitle && potentialTitle.toLowerCase() !== "untitled") {
      title = potentialTitle;
    }
  }

  return (
    <ChainOfThoughtStep
      key={id}
      className="cursor-pointer"
      label={t.toolCalls.viewWebPage}
      icon={GlobeIcon}
      onClick={() => {
        window.open(url, "_blank");
      }}
    >
      <ChainOfThoughtSearchResult>
        {url && (
          <a href={url} target="_blank" rel="noreferrer">
            {title}
          </a>
        )}
      </ChainOfThoughtSearchResult>
    </ChainOfThoughtStep>
  );
}
