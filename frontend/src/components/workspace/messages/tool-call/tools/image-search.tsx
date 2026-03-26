"use client";

import { SearchIcon } from "lucide-react";

import {
  ChainOfThoughtSearchResult,
  ChainOfThoughtSearchResults,
  ChainOfThoughtStep,
} from "@/components/ai-elements/chain-of-thought";
import { Tooltip } from "@/components/workspace/tooltip";

import type { ToolCallProps, ToolCallContext } from "../types";

interface Props extends ToolCallProps, ToolCallContext {
  t: {
    toolCalls: {
      searchForRelatedImages: string;
      searchForRelatedImagesFor: (query: string) => string;
    };
  };
}

export function ImageSearchRenderer({ id, args, result, t }: Props) {
  let label: React.ReactNode = t.toolCalls.searchForRelatedImages;
  if (typeof args.query === "string") {
    label = t.toolCalls.searchForRelatedImagesFor(args.query);
  }

  const results = (
    result as {
      results: {
        source_url: string;
        thumbnail_url: string;
        image_url: string;
        title: string;
      }[];
    }
  )?.results;

  return (
    <ChainOfThoughtStep key={id} label={label} icon={SearchIcon}>
      {Array.isArray(results) && (
        <ChainOfThoughtSearchResults>
          {Array.isArray(results) &&
            results.map((item) => (
              <Tooltip key={item.image_url} content={item.title}>
                <a
                  className="size-24 overflow-hidden rounded-lg object-cover"
                  href={item.source_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  <div className="bg-accent size-24">
                    <img
                      className="size-full object-cover"
                      src={item.thumbnail_url}
                      alt={item.title}
                      width={100}
                      height={100}
                    />
                  </div>
                </a>
              </Tooltip>
            ))}
        </ChainOfThoughtSearchResults>
      )}
    </ChainOfThoughtStep>
  );
}
