"use client";

import { SearchIcon } from "lucide-react";

import {
  ChainOfThoughtSearchResult,
  ChainOfThoughtSearchResults,
  ChainOfThoughtStep,
} from "@/components/ai-elements/chain-of-thought";

import type { ToolCallProps, ToolCallContext } from "../types";

interface Props extends ToolCallProps, ToolCallContext {
  t: {
    toolCalls: {
      searchForRelatedInfo: string;
      searchOnWebFor: (query: string) => string;
    };
  };
}

export function WebSearchRenderer({ id, args, result, t }: Props) {
  let label: React.ReactNode = t.toolCalls.searchForRelatedInfo;
  if (typeof args.query === "string") {
    label = t.toolCalls.searchOnWebFor(args.query);
  }

  return (
    <ChainOfThoughtStep key={id} label={label} icon={SearchIcon}>
      {Array.isArray(result) && (
        <ChainOfThoughtSearchResults>
          {result.map((item) => (
            <ChainOfThoughtSearchResult key={item.url}>
              <a href={item.url} target="_blank" rel="noreferrer">
                {item.title}
              </a>
            </ChainOfThoughtSearchResult>
          ))}
        </ChainOfThoughtSearchResults>
      )}
    </ChainOfThoughtStep>
  );
}
