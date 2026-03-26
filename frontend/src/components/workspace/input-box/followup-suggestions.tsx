"use client";

import { XIcon } from "lucide-react";

import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/core/i18n/hooks";

interface FollowupSuggestionsProps {
  followups: string[];
  followupsLoading: boolean;
  followupsHidden: boolean;
  setFollowupsHidden: (hidden: boolean) => void;
  onFollowupClick: (suggestion: string) => void;
  disabled?: boolean;
}

export function FollowupSuggestions({
  followups,
  followupsLoading,
  followupsHidden,
  setFollowupsHidden,
  onFollowupClick,
  disabled,
}: FollowupSuggestionsProps) {
  const { t } = useI18n();

  if (disabled || followupsHidden || (!followupsLoading && followups.length === 0)) {
    return null;
  }

  return (
    <div className="absolute right-0 -top-20 left-0 z-20 flex items-center justify-center">
      <div className="flex items-center gap-2">
        {followupsLoading ? (
          <div className="text-muted-foreground bg-background/80 rounded-full border px-4 py-2 text-xs backdrop-blur-sm">
            {t.inputBox.followupLoading}
          </div>
        ) : (
          <Suggestions className="min-h-16 w-fit items-start">
            {followups.map((s) => (
              <Suggestion
                key={s}
                suggestion={s}
                onClick={() => onFollowupClick(s)}
              />
            ))}
            <Button
              aria-label={t.common.close}
              className="text-muted-foreground cursor-pointer rounded-full px-3 text-xs font-normal"
              variant="outline"
              size="sm"
              type="button"
              onClick={() => setFollowupsHidden(true)}
            >
              <XIcon className="size-4" />
            </Button>
          </Suggestions>
        )}
      </div>
    </div>
  );
}
