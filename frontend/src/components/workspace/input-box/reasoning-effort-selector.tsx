"use client";

import { CheckIcon } from "lucide-react";

import {
  PromptInputActionMenu,
  PromptInputActionMenuContent,
  PromptInputActionMenuItem,
  PromptInputActionMenuTrigger,
} from "@/components/ai-elements/prompt-input";
import {
  DropdownMenuGroup,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

type ReasoningEffort = "minimal" | "low" | "medium" | "high";

interface ReasoningEffortSelectorProps {
  reasoningEffort: ReasoningEffort | undefined;
  onSelect: (effort: ReasoningEffort) => void;
}

export function ReasoningEffortSelector({
  reasoningEffort,
  onSelect,
}: ReasoningEffortSelectorProps) {
  const { t } = useI18n();

  const currentEffort = reasoningEffort ?? "medium";

  const getEffortLabel = (effort: ReasoningEffort) => {
    switch (effort) {
      case "minimal":
        return t.inputBox.reasoningEffortMinimal;
      case "low":
        return t.inputBox.reasoningEffortLow;
      case "medium":
        return t.inputBox.reasoningEffortMedium;
      case "high":
        return t.inputBox.reasoningEffortHigh;
    }
  };

  return (
    <PromptInputActionMenu>
      <PromptInputActionMenuTrigger className="gap-1! px-2!">
        <div className="text-xs font-normal">
          {t.inputBox.reasoningEffort}:{getEffortLabel(currentEffort)}
        </div>
      </PromptInputActionMenuTrigger>
      <PromptInputActionMenuContent className="w-70">
        <DropdownMenuGroup>
          <DropdownMenuLabel className="text-muted-foreground text-xs">
            {t.inputBox.reasoningEffort}
          </DropdownMenuLabel>
          <PromptInputActionMenu>
            <ReasoningEffortMenuItem
              effort="minimal"
              label={t.inputBox.reasoningEffortMinimal}
              description={t.inputBox.reasoningEffortMinimalDescription}
              isSelected={currentEffort === "minimal"}
              onSelect={onSelect}
            />
            <ReasoningEffortMenuItem
              effort="low"
              label={t.inputBox.reasoningEffortLow}
              description={t.inputBox.reasoningEffortLowDescription}
              isSelected={currentEffort === "low"}
              onSelect={onSelect}
            />
            <ReasoningEffortMenuItem
              effort="medium"
              label={t.inputBox.reasoningEffortMedium}
              description={t.inputBox.reasoningEffortMediumDescription}
              isSelected={currentEffort === "medium"}
              onSelect={onSelect}
            />
            <ReasoningEffortMenuItem
              effort="high"
              label={t.inputBox.reasoningEffortHigh}
              description={t.inputBox.reasoningEffortHighDescription}
              isSelected={currentEffort === "high"}
              onSelect={onSelect}
            />
          </PromptInputActionMenu>
        </DropdownMenuGroup>
      </PromptInputActionMenuContent>
    </PromptInputActionMenu>
  );
}

interface ReasoningEffortMenuItemProps {
  effort: ReasoningEffort;
  label: string;
  description: string;
  isSelected: boolean;
  onSelect: (effort: ReasoningEffort) => void;
}

function ReasoningEffortMenuItem({
  effort,
  label,
  description,
  isSelected,
  onSelect,
}: ReasoningEffortMenuItemProps) {
  return (
    <PromptInputActionMenuItem
      className={cn(
        isSelected ? "text-accent-foreground" : "text-muted-foreground/65",
      )}
      onSelect={() => onSelect(effort)}
    >
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-1 font-bold">{label}</div>
        <div className="pl-2 text-xs">{description}</div>
      </div>
      {isSelected ? (
        <CheckIcon className="ml-auto size-4" />
      ) : (
        <div className="ml-auto size-4" />
      )}
    </PromptInputActionMenuItem>
  );
}
