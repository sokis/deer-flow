"use client";

import {
  CheckIcon,
  GraduationCapIcon,
  LightbulbIcon,
  RocketIcon,
  ZapIcon,
} from "lucide-react";

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

import { ModeHoverGuide } from "../mode-hover-guide";

type InputMode = "flash" | "thinking" | "pro" | "ultra";

interface ModeSelectorProps {
  mode: InputMode | undefined;
  supportThinking: boolean;
  onModeSelect: (mode: InputMode) => void;
}

export function ModeSelector({
  mode,
  supportThinking,
  onModeSelect,
}: ModeSelectorProps) {
  const { t } = useI18n();

  const currentMode =
    mode === "flash" || mode === "thinking" || mode === "pro" || mode === "ultra"
      ? mode
      : "flash";

  return (
    <PromptInputActionMenu>
      <ModeHoverGuide mode={currentMode}>
        <PromptInputActionMenuTrigger className="gap-1! px-2!">
          <div>
            {currentMode === "flash" && <ZapIcon className="size-3" />}
            {currentMode === "thinking" && (
              <LightbulbIcon className="size-3" />
            )}
            {currentMode === "pro" && (
              <GraduationCapIcon className="size-3" />
            )}
            {currentMode === "ultra" && (
              <RocketIcon className="size-3 text-[#dabb5e]" />
            )}
          </div>
          <div
            className={cn(
              "text-xs font-normal",
              currentMode === "ultra" ? "golden-text" : "",
            )}
          >
            {(currentMode === "flash" && t.inputBox.flashMode) ||
              (currentMode === "thinking" && t.inputBox.reasoningMode) ||
              (currentMode === "pro" && t.inputBox.proMode) ||
              (currentMode === "ultra" && t.inputBox.ultraMode)}
          </div>
        </PromptInputActionMenuTrigger>
      </ModeHoverGuide>
      <PromptInputActionMenuContent className="w-80">
        <DropdownMenuGroup>
          <DropdownMenuLabel className="text-muted-foreground text-xs">
            {t.inputBox.mode}
          </DropdownMenuLabel>
          <PromptInputActionMenu>
            <ModeMenuItem
              mode="flash"
              label={t.inputBox.flashMode}
              description={t.inputBox.flashModeDescription}
              icon={<ZapIcon className="mr-2 size-4" />}
              isSelected={currentMode === "flash"}
              onSelect={onModeSelect}
            />
            {supportThinking && (
              <ModeMenuItem
                mode="thinking"
                label={t.inputBox.reasoningMode}
                description={t.inputBox.reasoningModeDescription}
                icon={<LightbulbIcon className="mr-2 size-4" />}
                isSelected={currentMode === "thinking"}
                onSelect={onModeSelect}
              />
            )}
            <ModeMenuItem
              mode="pro"
              label={t.inputBox.proMode}
              description={t.inputBox.proModeDescription}
              icon={<GraduationCapIcon className="mr-2 size-4" />}
              isSelected={currentMode === "pro"}
              onSelect={onModeSelect}
            />
            <ModeMenuItem
              mode="ultra"
              label={t.inputBox.ultraMode}
              description={t.inputBox.ultraModeDescription}
              icon={<RocketIcon className="mr-2 size-4" />}
              isSelected={currentMode === "ultra"}
              isGolden
              onSelect={onModeSelect}
            />
          </PromptInputActionMenu>
        </DropdownMenuGroup>
      </PromptInputActionMenuContent>
    </PromptInputActionMenu>
  );
}

interface ModeMenuItemProps {
  mode: InputMode;
  label: string;
  description: string;
  icon: React.ReactNode;
  isSelected: boolean;
  isGolden?: boolean;
  onSelect: (mode: InputMode) => void;
}

function ModeMenuItem({
  mode,
  label,
  description,
  icon,
  isSelected,
  isGolden,
  onSelect,
}: ModeMenuItemProps) {
  return (
    <PromptInputActionMenuItem
      className={cn(
        isSelected ? "text-accent-foreground" : "text-muted-foreground/65",
      )}
      onSelect={() => onSelect(mode)}
    >
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-1 font-bold">
          <span
            className={cn(
              isSelected && (isGolden ? "text-[#dabb5e]" : "text-accent-foreground"),
            )}
          >
            {icon}
          </span>
          <span className={cn(isSelected && isGolden && "golden-text")}>
            {label}
          </span>
        </div>
        <div className="pl-7 text-xs">{description}</div>
      </div>
      {isSelected ? (
        <CheckIcon className="ml-auto size-4" />
      ) : (
        <div className="ml-auto size-4" />
      )}
    </PromptInputActionMenuItem>
  );
}
