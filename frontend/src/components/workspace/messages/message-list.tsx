import type { BaseStream } from "@langchain/langgraph-sdk/react";

import {
  Conversation,
  ConversationContent,
} from "@/components/ai-elements/conversation";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { RotateCcw } from "lucide-react";
import { useState } from "react";

import { useI18n } from "@/core/i18n/hooks";
import {
  extractContentFromMessage,
  extractPresentFilesFromMessage,
  extractTextFromMessage,
  groupMessages,
  hasContent,
  hasPresentFiles,
  hasReasoning,
} from "@/core/messages/utils";
import { useRehypeSplitWordsIntoSpans } from "@/core/rehype";
import type { Subtask } from "@/core/tasks";
import { useUpdateSubtask } from "@/core/tasks/context";
import type { AgentThreadState } from "@/core/threads";
import { cn } from "@/lib/utils";

import { ArtifactFileList } from "../artifacts/artifact-file-list";
import { StreamingIndicator } from "../streaming-indicator";

import { MarkdownContent } from "./markdown-content";
import { MessageGroup } from "./message-group";
import { MessageListItem } from "./message-list-item";
import { MessageListSkeleton } from "./skeleton";
import { SubtaskCard } from "./subtask-card";

function RewindButton({
  turnIndex,
  onConfirm,
  isLoading,
}: {
  turnIndex: number;
  onConfirm: (turnIndex: number) => void;
  isLoading?: boolean;
}) {
  return (
    <button
      className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-muted rounded absolute -right-8 top-0"
      onClick={() => onConfirm(turnIndex)}
      disabled={isLoading}
      title="回退到此轮之前"
    >
      <RotateCcw className="h-4 w-4 text-muted-foreground" />
    </button>
  );
}

export function MessageList({
  className,
  threadId,
  thread,
  paddingBottom = 160,
  onRewind,
  isRewinding,
}: {
  className?: string;
  threadId: string;
  thread: BaseStream<AgentThreadState>;
  paddingBottom?: number;
  onRewind?: (turnIndex: number) => void;
  isRewinding?: boolean;
}) {
  const { t } = useI18n();
  const rehypePlugins = useRehypeSplitWordsIntoSpans(thread.isLoading);
  const updateSubtask = useUpdateSubtask();
  const messages = thread.messages;
  const [confirmRewindTurn, setConfirmRewindTurn] = useState<number | null>(null);
  let turnIndex = 0;
  if (thread.isThreadLoading && messages.length === 0) {
    return <MessageListSkeleton />;
  }
  return (
    <Conversation
      className={cn("flex size-full flex-col justify-center", className)}
    >
      <ConversationContent className="mx-auto w-full max-w-(--container-width-md) gap-8 pt-12">
        {groupMessages(messages, (group) => {
          if (group.type === "human" || group.type === "assistant") {
            const currentTurnIndex = turnIndex;
            if (group.type === "human") {
              turnIndex++;
            }
            return (
              <div key={`${group.id}`} className="group relative">
                {group.messages.map((msg) => (
                  <MessageListItem
                    key={`${group.id}/${msg.id}`}
                    message={msg}
                    isLoading={thread.isLoading}
                  />
                ))}
                {group.type === "human" && onRewind && (
                  <RewindButton
                    turnIndex={currentTurnIndex}
                    onConfirm={(idx) => setConfirmRewindTurn(idx)}
                    isLoading={isRewinding}
                  />
                )}
              </div>
            );
          } else if (group.type === "assistant:clarification") {
            const message = group.messages[0];
            if (message && hasContent(message)) {
              return (
                <MarkdownContent
                  key={group.id}
                  content={extractContentFromMessage(message)}
                  isLoading={thread.isLoading}
                  rehypePlugins={rehypePlugins}
                />
              );
            }
            return null;
          } else if (group.type === "assistant:present-files") {
            const files: string[] = [];
            for (const message of group.messages) {
              if (hasPresentFiles(message)) {
                const presentFiles = extractPresentFilesFromMessage(message);
                files.push(...presentFiles);
              }
            }
            return (
              <div className="w-full" key={group.id}>
                {group.messages[0] && hasContent(group.messages[0]) && (
                  <MarkdownContent
                    content={extractContentFromMessage(group.messages[0])}
                    isLoading={thread.isLoading}
                    rehypePlugins={rehypePlugins}
                    className="mb-4"
                  />
                )}
                <ArtifactFileList files={files} threadId={threadId} />
              </div>
            );
          } else if (group.type === "assistant:subagent") {
            const tasks = new Set<Subtask>();
            for (const message of group.messages) {
              if (message.type === "ai") {
                for (const toolCall of message.tool_calls ?? []) {
                  if (toolCall.name === "task") {
                    const task: Subtask = {
                      id: toolCall.id!,
                      subagent_type: toolCall.args.subagent_type,
                      description: toolCall.args.description,
                      prompt: toolCall.args.prompt,
                      status: "in_progress",
                    };
                    updateSubtask(task);
                    tasks.add(task);
                  }
                }
              } else if (message.type === "tool") {
                const taskId = message.tool_call_id;
                if (taskId) {
                  const result = extractTextFromMessage(message);
                  if (result.startsWith("Task Succeeded. Result:")) {
                    updateSubtask({
                      id: taskId,
                      status: "completed",
                      result: result
                        .split("Task Succeeded. Result:")[1]
                        ?.trim(),
                    });
                  } else if (result.startsWith("Task failed.")) {
                    updateSubtask({
                      id: taskId,
                      status: "failed",
                      error: result.split("Task failed.")[1]?.trim(),
                    });
                  } else if (result.startsWith("Task timed out")) {
                    updateSubtask({
                      id: taskId,
                      status: "failed",
                      error: result,
                    });
                  } else {
                    updateSubtask({
                      id: taskId,
                      status: "in_progress",
                    });
                  }
                }
              }
            }
            const results: React.ReactNode[] = [];
            for (const message of group.messages.filter(
              (message) => message.type === "ai",
            )) {
              if (hasReasoning(message)) {
                results.push(
                  <MessageGroup
                    key={"thinking-group-" + message.id}
                    messages={[message]}
                    isLoading={thread.isLoading}
                  />,
                );
              }
              results.push(
                <div
                  key="subtask-count"
                  className="text-muted-foreground font-norma pt-2 text-sm"
                >
                  {t.subtasks.executing(tasks.size)}
                </div>,
              );
              const taskIds = message.tool_calls?.map(
                (toolCall) => toolCall.id,
              );
              for (const taskId of taskIds ?? []) {
                results.push(
                  <SubtaskCard
                    key={"task-group-" + taskId}
                    taskId={taskId!}
                    isLoading={thread.isLoading}
                  />,
                );
              }
            }
            return (
              <div
                key={"subtask-group-" + group.id}
                className="relative z-1 flex flex-col gap-2"
              >
                {results}
              </div>
            );
          }
          return (
            <MessageGroup
              key={"group-" + group.id}
              messages={group.messages}
              isLoading={thread.isLoading}
            />
          );
        })}
        {thread.isLoading && <StreamingIndicator className="my-4" />}
        <div style={{ height: `${paddingBottom}px` }} />
        <Dialog
          open={confirmRewindTurn !== null}
          onOpenChange={(open) => !open && setConfirmRewindTurn(null)}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>确认回退</DialogTitle>
              <DialogDescription>
                回退将丢失此轮之后的全部进度，是否继续？
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <button onClick={() => setConfirmRewindTurn(null)}>取消</button>
              <button
                onClick={() => {
                  if (confirmRewindTurn !== null) {
                    onRewind?.(confirmRewindTurn);
                    setConfirmRewindTurn(null);
                  }
                }}
                disabled={isRewinding}
              >
                {isRewinding ? "回退中..." : "确认回退"}
              </button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </ConversationContent>
    </Conversation>
  );
}
