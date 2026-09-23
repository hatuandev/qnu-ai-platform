export type ConversationStatus =
  | "ai_active"
  | "handoff_requested"
  | "staff_claimed"
  | "resolved";

export type MessageSender = "user" | "assistant" | "agent";

export interface ConversationMessage {
  id: string;
  thread_id: string;
  sender: MessageSender;
  text: string;
  created_at: string;
}

export interface ConversationThreadItem {
  id: string;
  assistant_code: string;
  assistant_name: string;
  user_name: string;
  user_email?: string | null;
  last_message: string;
  status: ConversationStatus;
  assigned_to?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationThreadDetail extends ConversationThreadItem {
  messages: ConversationMessage[];
}

export interface ConversationReplyRequest {
  text: string;
  staff_name?: string;
}

export interface ConversationStatusUpdateRequest {
  status: ConversationStatus;
  assigned_to?: string;
}
