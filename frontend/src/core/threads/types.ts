import type { Message, Thread } from "@langchain/langgraph-sdk";

import type { Todo } from "../todos";

export interface AgentThreadState extends Record<string, unknown> {
  title: string;
  messages: Message[];
  artifacts: string[];
  todos?: Todo[];
}

export interface AgentThread extends Thread<AgentThreadState> {}

export interface AgentThreadContext extends Record<string, unknown> {
  thread_id: string;
  model_name: string | undefined;
  thinking_enabled: boolean;
  is_plan_mode: boolean;
  subagent_enabled: boolean;
  reasoning_effort?: "minimal" | "low" | "medium" | "high";
  agent_name?: string;
}

export type ThreadProgressKind =
  | "message"
  | "tool"
  | "subtask"
  | "update"
  | "finish"
  | null;

export interface ThreadStreamObservability {
  activeThreadId: string | null;
  requestStartedAt: number | null;
  firstResponseAt: number | null;
  lastProgressAt: number | null;
  finishedAt: number | null;
  lastError: string | null;
  messageDelta: number;
  toolCallCount: number;
  subtaskCount: number;
  updateCount: number;
  lastProgressKind: ThreadProgressKind;
}

export type ThreadRunTruthPhase =
  | "idle"
  | "waiting"
  | "running"
  | "stuck"
  | "completed"
  | "error"
  | "interrupted";

export interface ThreadRunHealth {
  thread_id: string;
  run_id: string | null;
  status_raw: string | null;
  truth_phase: ThreadRunTruthPhase;
  reason_code: string;
  created_at: string | null;
  updated_at: string | null;
  last_progress_at: string | null;
  last_progress_source: string | null;
  checkpoint_created_at: string | null;
  idle_seconds: number | null;
  message_count: number;
  next_nodes: string[];
}
