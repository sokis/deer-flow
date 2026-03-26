export interface ToolCallProps {
  id?: string;
  messageId?: string;
  name: string;
  args: Record<string, unknown>;
  result?: string | Record<string, unknown>;
  isLast?: boolean;
  isLoading?: boolean;
}

export interface ToolCallContext {
  setOpen: (open: boolean) => void;
  autoOpen: boolean;
  autoSelect: boolean;
  selectedArtifact: string | null;
  select: (url: string, autoSelect?: boolean) => void;
}

export interface ToolHandler {
  canHandle(name: string): boolean;
  render(props: ToolCallProps, context: ToolCallContext): React.ReactNode;
}
