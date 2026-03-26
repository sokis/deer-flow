"use client";

import {
  ActivityIcon,
  AlertTriangleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  CircleCheckBigIcon,
  CopyIcon,
  GripVerticalIcon,
  LoaderCircleIcon,
  RefreshCwIcon,
  SquareIcon,
  WifiIcon,
  WifiOffIcon,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { useI18n } from "@/core/i18n/hooks";
import type {
  ThreadRunHealth,
  ThreadStreamObservability,
} from "@/core/threads/types";
import { cn } from "@/lib/utils";

type StreamObservabilityPanelProps = {
  observability: ThreadStreamObservability;
  runHealth?: ThreadRunHealth | null;
  isLoading: boolean;
  isUploading: boolean;
  canStop?: boolean;
  onRefresh?: () => void;
  onReconnect?: () => void;
  onStop?: () => void | Promise<void>;
  className?: string;
};

type PanelPhase =
  | "uploading"
  | "waiting"
  | "running"
  | "silent"
  | "suspectedStuck"
  | "completed"
  | "error";

const WAITING_LONG_MS = 30000;
const SILENT_AFTER_MS = 30000;
const SUSPECTED_STUCK_AFTER_MS = 120000;
const RECENTLY_FINISHED_MS = 30000;

function formatDuration(ms: number) {
  const totalSeconds = Math.max(Math.floor(ms / 1000), 0);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) {
    return `${seconds}s`;
  }
  return `${minutes}m ${seconds}s`;
}

function formatAgo(ms: number, fallback: string) {
  if (ms < 1000) {
    return fallback;
  }
  return formatDuration(ms);
}

function Metric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="bg-background/60 rounded-lg border px-3 py-2">
      <div className="text-muted-foreground text-[11px]">{label}</div>
      <div className="mt-1 text-sm font-medium">{value}</div>
    </div>
  );
}

export function StreamObservabilityPanel({
  observability,
  runHealth,
  isLoading,
  isUploading,
  canStop = false,
  onRefresh,
  onReconnect,
  onStop,
  className,
}: StreamObservabilityPanelProps) {
  const { t } = useI18n();
  const [now, setNow] = useState(() => Date.now());
  const [open, setOpen] = useState(false);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const backendStartedAt = runHealth?.created_at
    ? Date.parse(runHealth.created_at)
    : null;
  const startedAt = observability.requestStartedAt ?? backendStartedAt ?? now;
  const dragStateRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    initialX: number;
    initialY: number;
  } | null>(null);

  useEffect(() => {
    if (!isLoading && !isUploading && !observability.finishedAt) {
      return;
    }
    const timer = window.setInterval(() => {
      setNow(Date.now());
    }, 1000);
    return () => window.clearInterval(timer);
  }, [isLoading, isUploading, observability.finishedAt]);

  const activeSince = observability.requestStartedAt ?? backendStartedAt;
  const elapsedMs =
    activeSince === null ? 0 : (observability.finishedAt ?? now) - activeSince;
  const finishedAgo = observability.finishedAt
    ? now - observability.finishedAt
    : null;
  const shouldShow =
    (activeSince !== null || (runHealth && runHealth.truth_phase !== "idle")) &&
    (isLoading ||
      isUploading ||
      Boolean(runHealth && runHealth.truth_phase !== "idle") ||
      Boolean(observability.lastError) ||
      (finishedAgo !== null && finishedAgo < RECENTLY_FINISHED_MS));

  const phase = useMemo<PanelPhase | null>(() => {
    if (!shouldShow) {
      return null;
    }
    if (observability.lastError) {
      return "error";
    }
    if (isUploading) {
      return "uploading";
    }
    if (runHealth?.truth_phase === "error") {
      return "error";
    }
    if (
      runHealth?.truth_phase === "completed" ||
      runHealth?.truth_phase === "interrupted" ||
      runHealth?.truth_phase === "idle"
    ) {
      return "completed";
    }
    if (runHealth?.truth_phase === "stuck") {
      return "suspectedStuck";
    }
    if (runHealth?.truth_phase === "waiting") {
      return "waiting";
    }
    if (runHealth?.truth_phase === "running") {
      return "running";
    }
    if (isLoading) {
      const idleSince =
        observability.lastProgressAt ?? observability.requestStartedAt;
      const idleMs = idleSince ? now - idleSince : 0;
      if (!observability.firstResponseAt) {
        return "waiting";
      }
      if (idleMs >= SUSPECTED_STUCK_AFTER_MS) {
        return "suspectedStuck";
      }
      if (idleMs >= SILENT_AFTER_MS) {
        return "silent";
      }
      return "running";
    }
    return "completed";
  }, [
    runHealth?.truth_phase,
    isLoading,
    isUploading,
    now,
    observability.firstResponseAt,
    observability.lastError,
    observability.lastProgressAt,
    observability.requestStartedAt,
    shouldShow,
  ]);

  const lastProgressLagMs =
    observability.lastProgressAt === null
      ? null
      : now - observability.lastProgressAt;
  const firstResponseMs =
    observability.firstResponseAt === null
      ? null
      : observability.firstResponseAt - startedAt;
  const idleMs =
    observability.lastProgressAt === null
      ? now - startedAt
      : now - observability.lastProgressAt;

  useEffect(() => {
    if (phase === "suspectedStuck" || phase === "error") {
      setOpen(true);
    }
  }, [phase]);

  useEffect(() => {
    const handlePointerMove = (event: PointerEvent) => {
      const dragState = dragStateRef.current;
      if (dragState?.pointerId !== event.pointerId) {
        return;
      }
      setOffset({
        x: dragState.initialX + event.clientX - dragState.startX,
        y: dragState.initialY + event.clientY - dragState.startY,
      });
    };

    const handlePointerUp = (event: PointerEvent) => {
      const dragState = dragStateRef.current;
      if (dragState?.pointerId !== event.pointerId) {
        return;
      }
      dragStateRef.current = null;
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerUp);
    };
  }, []);

  const handleDragStart = (event: React.PointerEvent<HTMLButtonElement>) => {
    dragStateRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      initialX: offset.x,
      initialY: offset.y,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  if (!shouldShow || !phase || !activeSince) {
    return null;
  }

  const statusMeta = {
    uploading: {
      label: t.observability.statuses.uploading,
      description: t.observability.descriptions.uploading,
      summary: t.observability.descriptions.uploading,
      rationale: t.observability.reasons.waitingShort,
      action: t.observability.actions.waiting,
      badgeVariant: "secondary" as const,
      icon: LoaderCircleIcon,
      iconClassName: "animate-spin text-primary",
      bubbleClassName: "border-primary/20 bg-primary/5 text-primary-foreground",
    },
    waiting: {
      label: t.observability.statuses.waiting,
      description: t.observability.descriptions.waiting,
      summary:
        elapsedMs > WAITING_LONG_MS
          ? t.observability.reasons.waitingLong
          : t.observability.reasons.waitingShort,
      rationale:
        elapsedMs > WAITING_LONG_MS
          ? t.observability.reasons.waitingLong
          : t.observability.reasons.waitingShort,
      action: t.observability.actions.waiting,
      badgeVariant: "secondary" as const,
      icon: WifiIcon,
      iconClassName: "text-primary",
      bubbleClassName: "border-border/80 bg-background/90",
    },
    running: {
      label: t.observability.statuses.running,
      description: t.observability.descriptions.running,
      summary: `${t.observability.reasons.runningRecent} ${t.observability.lastProgress} ${formatAgo(
        lastProgressLagMs ?? 0,
        t.observability.justNow,
      )}`,
      rationale: t.observability.reasons.runningRecent,
      action: t.observability.actions.running,
      badgeVariant: "default" as const,
      icon: ActivityIcon,
      iconClassName: "text-primary",
      bubbleClassName: "border-primary/20 bg-primary/5",
    },
    silent: {
      label: t.observability.statuses.silent,
      description: t.observability.descriptions.silent,
      summary: `${t.observability.reasons.silentShort} ${t.observability.lastProgress} ${formatAgo(
        idleMs,
        t.observability.justNow,
      )}`,
      rationale: t.observability.reasons.silentShort,
      action: t.observability.actions.silent,
      badgeVariant: "outline" as const,
      icon: WifiIcon,
      iconClassName: "text-amber-500",
      bubbleClassName: "border-amber-500/30 bg-amber-500/5",
    },
    suspectedStuck: {
      label: t.observability.statuses.suspectedStuck,
      description: t.observability.descriptions.suspectedStuck,
      summary: `${t.observability.reasons.silentLong} ${t.observability.lastProgress} ${formatAgo(
        idleMs,
        t.observability.justNow,
      )}`,
      rationale: t.observability.reasons.silentLong,
      action: t.observability.actions.suspectedStuck,
      badgeVariant: "destructive" as const,
      icon: WifiOffIcon,
      iconClassName: "text-destructive",
      bubbleClassName: "border-destructive/30 bg-destructive/5",
    },
    completed: {
      label: t.observability.statuses.completed,
      description: t.observability.descriptions.completed,
      summary: t.observability.reasons.completedRecent,
      rationale: t.observability.reasons.completedRecent,
      action: t.observability.actions.completed,
      badgeVariant: "outline" as const,
      icon: CircleCheckBigIcon,
      iconClassName: "text-emerald-600",
      bubbleClassName: "border-emerald-500/20 bg-emerald-500/5",
    },
    error: {
      label: t.observability.statuses.error,
      description: observability.lastError ?? t.observability.descriptions.error,
      summary: observability.lastError ?? t.observability.reasons.errorDetected,
      rationale: t.observability.reasons.errorDetected,
      action: t.observability.actions.error,
      badgeVariant: "destructive" as const,
      icon: AlertTriangleIcon,
      iconClassName: "text-destructive",
      bubbleClassName: "border-destructive/30 bg-destructive/5",
    },
  }[phase];

  const Icon = statusMeta.icon;

  const progressKindLabel = {
    message: t.observability.progressKinds.message,
    tool: t.observability.progressKinds.tool,
    subtask: t.observability.progressKinds.subtask,
    update: t.observability.progressKinds.update,
    finish: t.observability.progressKinds.finish,
    null: t.observability.progressKinds.none,
  }[
    String(observability.lastProgressKind) as
      | "message"
      | "tool"
      | "subtask"
      | "update"
      | "finish"
      | "null"
  ];

  const handleCopyThreadId = async () => {
    if (!observability.activeThreadId) {
      return;
    }
    await navigator.clipboard.writeText(observability.activeThreadId);
    toast.success(t.observability.copied);
  };

  const nextNodesText =
    runHealth?.next_nodes && runHealth.next_nodes.length > 0
      ? runHealth.next_nodes.join(", ")
      : t.observability.noNextNode;
  const backendProgressValue =
    runHealth?.idle_seconds == null
      ? t.observability.noProgressYet
      : `${formatDuration(runHealth.idle_seconds * 1000)} · ${runHealth.last_progress_source ?? t.observability.noProgressYet}`;

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <div
        className={cn("flex justify-end", className)}
        style={{ transform: `translate(${offset.x}px, ${offset.y}px)` }}
      >
        <div className="max-w-full min-w-0">
          <div
            className={cn(
              "bg-background/88 rounded-2xl border shadow-sm backdrop-blur-sm",
              statusMeta.bubbleClassName,
            )}
          >
            <div className="flex items-center gap-2 px-3 py-2">
              <Button
                size="icon-sm"
                variant="ghost"
                className="cursor-grab active:cursor-grabbing"
                aria-label={t.observability.bubbleTitle}
                onPointerDown={handleDragStart}
              >
                <GripVerticalIcon />
              </Button>
              <Icon className={cn("size-4 shrink-0", statusMeta.iconClassName)} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-medium">
                    {statusMeta.label}
                  </span>
                  <Badge variant={statusMeta.badgeVariant}>
                    {formatDuration(elapsedMs)}
                  </Badge>
                </div>
                <div className="text-muted-foreground mt-0.5 line-clamp-1 text-xs">
                  {statusMeta.summary}
                </div>
              </div>
              <CollapsibleTrigger asChild>
                <Button
                  size="icon-sm"
                  variant="ghost"
                  aria-label={open ? t.observability.collapse : t.observability.expand}
                >
                  {open ? <ChevronUpIcon /> : <ChevronDownIcon />}
                </Button>
              </CollapsibleTrigger>
            </div>
            <CollapsibleContent>
              <div className="border-border/60 border-t px-3 py-3">
                <div className="grid gap-3">
                  <div className="grid gap-1">
                    <div className="text-muted-foreground text-[11px]">
                      {t.observability.activeConclusion}
                    </div>
                    <div className="text-sm font-medium">{statusMeta.description}</div>
                  </div>
                  <div className="grid gap-1">
                    <div className="text-muted-foreground text-[11px]">
                      {t.observability.rationale}
                    </div>
                    <div className="text-sm leading-6">{statusMeta.rationale}</div>
                  </div>
                  <div className="grid gap-1">
                    <div className="text-muted-foreground text-[11px]">
                      {t.observability.actionPlan}
                    </div>
                    <div className="text-sm leading-6">{statusMeta.action}</div>
                  </div>
                  {runHealth && runHealth.truth_phase !== "idle" && (
                    <div className="grid gap-1">
                      <div className="text-muted-foreground text-[11px]">
                        {t.observability.backendTruth}
                      </div>
                      <div className="text-sm leading-6">
                        {t.observability.rawStatus}：{runHealth.status_raw ?? t.observability.noProgressYet}
                      </div>
                      <div className="text-sm leading-6">
                        {t.observability.backendProgress}：{backendProgressValue}
                      </div>
                      <div className="text-sm leading-6">
                        {t.observability.nextNodes}：{nextNodesText}
                      </div>
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-2 lg:grid-cols-3">
                    <Metric
                      label={t.observability.elapsed}
                      value={formatDuration(elapsedMs)}
                    />
                    <Metric
                      label={t.observability.lastProgress}
                      value={
                        lastProgressLagMs === null
                          ? t.observability.noProgressYet
                          : `${formatAgo(lastProgressLagMs, t.observability.justNow)} · ${progressKindLabel}`
                      }
                    />
                    <Metric
                      label={t.observability.firstResponse}
                      value={
                        firstResponseMs === null
                          ? t.observability.noProgressYet
                          : `+${formatDuration(firstResponseMs)}`
                      }
                    />
                    <Metric
                      label={t.observability.outputMessages}
                      value={String(observability.messageDelta)}
                    />
                    <Metric
                      label={t.observability.toolCalls}
                      value={String(observability.toolCallCount)}
                    />
                    <Metric
                      label={t.observability.subtasks}
                      value={`${observability.subtaskCount} / ${observability.updateCount}`}
                    />
                  </div>
                  <div className="grid gap-1">
                    <div className="text-muted-foreground text-[11px]">
                      {t.observability.activeThread}
                    </div>
                    <div className="truncate font-mono text-xs">
                      {observability.activeThreadId ?? t.observability.unboundThread}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" variant="outline" onClick={onRefresh}>
                      <RefreshCwIcon />
                      {t.observability.refresh}
                    </Button>
                    <Button size="sm" variant="outline" onClick={onReconnect}>
                      <WifiIcon />
                      {t.observability.reconnect}
                    </Button>
                    <Button size="sm" variant="outline" onClick={handleCopyThreadId}>
                      <CopyIcon />
                      {t.observability.copyThreadId}
                    </Button>
                    {canStop && (
                      <Button size="sm" variant="destructive" onClick={onStop}>
                        <SquareIcon />
                        {t.observability.stopRun}
                      </Button>
                    )}
                  </div>
                  <div className="text-muted-foreground text-[11px] leading-5">
                    {runHealth && runHealth.truth_phase !== "idle"
                      ? t.observability.backendConnectedHint
                      : t.observability.frontendOnlyHint}
                  </div>
                </div>
              </div>
            </CollapsibleContent>
          </div>
        </div>
      </div>
    </Collapsible>
  );
}
