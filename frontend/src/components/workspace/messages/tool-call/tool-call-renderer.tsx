"use client";

import { useI18n } from "@/core/i18n/hooks";

import { useArtifacts } from "../../artifacts";

import { AskClarificationRenderer } from "./tools/ask-clarification";
import { BashRenderer } from "./tools/bash";
import { DefaultRenderer } from "./tools/default";
import { FileOperationsRenderer } from "./tools/file-operations";
import { ImageSearchRenderer } from "./tools/image-search";
import { WebFetchRenderer } from "./tools/web-fetch";
import { WebSearchRenderer } from "./tools/web-search";
import { WriteTodosRenderer } from "./tools/write-todos";
import type { ToolCallProps } from "./types";

export function ToolCallRenderer(props: ToolCallProps) {
  const { t } = useI18n();
  const { setOpen, autoOpen, autoSelect, selectedArtifact, select } =
    useArtifacts();

  const context = { setOpen, autoOpen, autoSelect, selectedArtifact, select };

  switch (props.name) {
    case "web_search":
      return <WebSearchRenderer {...props} {...context} t={t} />;
    case "image_search":
      return <ImageSearchRenderer {...props} {...context} t={t} />;
    case "web_fetch":
      return <WebFetchRenderer {...props} {...context} t={t} />;
    case "ls":
    case "read_file":
    case "write_file":
    case "str_replace":
      return <FileOperationsRenderer {...props} {...context} t={t} />;
    case "bash":
      return <BashRenderer {...props} {...context} t={t} />;
    case "ask_clarification":
      return <AskClarificationRenderer {...props} {...context} t={t} />;
    case "write_todos":
      return <WriteTodosRenderer {...props} {...context} t={t} />;
    default:
      return <DefaultRenderer {...props} {...context} t={t} />;
  }
}
