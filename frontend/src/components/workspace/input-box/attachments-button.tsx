"use client";

import { PaperclipIcon } from "lucide-react";

import { usePromptInputAttachments } from "@/components/ai-elements/prompt-input";
import { PromptInputButton } from "@/components/ai-elements/prompt-input";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

import { Tooltip } from "../tooltip";

interface AttachmentsButtonProps {
  className?: string;
}

export function AttachmentsButton({ className }: AttachmentsButtonProps) {
  const { t } = useI18n();
  const attachments = usePromptInputAttachments();

  return (
    <Tooltip content={t.inputBox.addAttachments}>
      <PromptInputButton
        className={cn("px-2!", className)}
        onClick={() => attachments.openFileDialog()}
      >
        <PaperclipIcon className="size-3" />
      </PromptInputButton>
    </Tooltip>
  );
}
