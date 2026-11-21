import { getAccessToken, getRefreshToken, setAccessToken, clearAuthStorage } from "@/lib/token-store";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  const res = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) {
    clearAuthStorage();
    return null;
  }
  const body = (await res.json()) as { access_token: string };
  setAccessToken(body.access_token);
  return body.access_token;
}

async function apiFetch<T>(path: string, init?: RequestInit, retry = true): Promise<T> {
  const headers = new Headers(init?.headers ?? {});
  const hasFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  if (!hasFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const token = getAccessToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${API_URL}${path}`, { ...init, headers });

  if (res.status === 401 && retry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return apiFetch<T>(path, init, false);
    }
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  doc_count: number;
}

export interface Document {
  id: string;
  knowledge_base_id: string;
  filename: string;
  file_type: string | null;
  file_url: string | null;
  upload_status: string | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  title: string | null;
  channel: string;
  external_chat_id: string | null;
  support_mode: "bot" | "waiting" | "human";
  assigned_staff_id: string | null;
  handoff_reason: string | null;
  handoff_at: string | null;
  summary: string | null;
  summary_updated_at: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string | null;
  message_count: number;
}

export interface MessageSender {
  id: string;
  username: string;
  role: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  sender_type: string;
  sender_id: string | null;
  sender: MessageSender | null;
  is_internal: boolean;
  content: string;
  rating: number | null;
  feedback_text: string | null;
  created_at: string;
}

export interface Citation {
  id: string;
  message_id: string;
  chunk_id: string;
  relevance_score: number | null;
  chunk_content: string | null;
  document_name: string | null;
}

export interface ToolCall {
  id: string;
  message_id?: string;
  tool_name: string;
  arguments: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  status: string;
  error_message?: string | null;
  duration_ms?: number | null;
  created_at?: string;
}

export interface ToolCallEvent {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  label: string;
  status: string;
}

export interface ToolResultEvent {
  id: string;
  name: string;
  status: "success" | "error";
  result?: Record<string, unknown> | null;
  error?: string | null;
  duration_ms: number;
}

export interface Stats {
  total_users: number;
  total_knowledge_bases: number;
  total_documents: number;
  total_conversations: number;
  total_messages: number;
}

export interface User {
  id: string;
  username: string;
  email: string;
  role: "admin" | "staff" | "user";
  is_active: boolean;
  created_at: string;
}

export interface SupportConversation {
  id: string;
  title: string | null;
  channel: string;
  external_chat_id: string | null;
  support_mode: "bot" | "waiting" | "human";
  handoff_reason: string | null;
  handoff_at: string | null;
  resolved_at: string | null;
  summary: string | null;
  summary_updated_at: string | null;
  assigned_staff_id: string | null;
  assigned_staff_username: string | null;
  customer_name: string;
  customer_username: string | null;
  customer_external_username: string | null;
  customer_is_linked: boolean;
  message_count: number;
  last_message_preview: string | null;
  last_message_at: string | null;
  waiting_seconds: number;
  created_at: string;
  updated_at: string | null;
}

export interface SupportConversationDetail extends SupportConversation {
  messages: Message[];
}

export interface SupportStats {
  waiting_count: number;
  assigned_to_me: number;
  active_count: number;
}

export interface SupportStaffOption {
  id: string;
  username: string;
  email: string;
  active_count: number;
}

export interface SupportAction {
  ok: boolean;
  support_mode: "bot" | "waiting" | "human";
  assigned_staff_id: string | null;
  resolved_at: string | null;
}

export interface SupportMessageResult {
  ok: boolean;
  delivered: boolean;
  warning: string | null;
  message: Message | null;
}

export interface AuthPayload {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export function listKnowledgeBases() {
  return apiFetch<KnowledgeBase[]>("/knowledge-bases");
}

export function getKnowledgeBase(id: string) {
  return apiFetch<KnowledgeBase>(`/knowledge-bases/${id}`);
}

export function createKnowledgeBase(data: { name: string; description?: string }) {
  return apiFetch<KnowledgeBase>("/knowledge-bases", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function deleteKnowledgeBase(id: string) {
  return apiFetch<void>(`/knowledge-bases/${id}`, { method: "DELETE" });
}

export function listDocuments(kbId: string) {
  return apiFetch<Document[]>(`/knowledge-bases/${kbId}/documents`);
}

export function getDocument(id: string) {
  return apiFetch<Document>(`/documents/${id}`);
}

export function uploadDocument(kbId: string, file: File): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<Document>(`/knowledge-bases/${kbId}/documents`, {
    method: "POST",
    body: formData,
  });
}

export function deleteDocument(id: string) {
  return apiFetch<void>(`/documents/${id}`, { method: "DELETE" });
}

export function listConversations() {
  return apiFetch<Conversation[]>("/conversations");
}

export function listAllConversations() {
  return apiFetch<Conversation[]>("/conversations?include_all=true");
}

export function createConversation(title?: string) {
  return apiFetch<Conversation>("/conversations", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

export function getConversation(id: string) {
  return apiFetch<Conversation>(`/conversations/${id}`);
}

export function deleteConversation(id: string) {
  return apiFetch<void>(`/conversations/${id}`, { method: "DELETE" });
}

export function listMessages(conversationId: string) {
  return apiFetch<Message[]>(`/conversations/${conversationId}/messages`);
}

export function getCitations(messageId: string) {
  return apiFetch<Citation[]>(`/messages/${messageId}/citations`);
}

export function getToolCalls(messageId: string) {
  return apiFetch<ToolCall[]>(`/messages/${messageId}/tool-calls`);
}

export function submitFeedback(messageId: string, data: { rating?: number; feedback_text?: string }) {
  return apiFetch<{ ok: boolean; handoff: boolean; support_mode: string }>(
    `/messages/${messageId}/feedback`,
    {
      method: "PATCH",
      body: JSON.stringify(data),
    },
  );
}

export interface HandoffEvent {
  support_mode: "bot" | "waiting" | "human";
  announce?: boolean;
  reason?: string | null;
  notice?: string | null;
}

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onDone: () => void;
  onToolCall?: (toolCall: ToolCallEvent) => void;
  onToolResult?: (toolResult: ToolResultEvent) => void;
  onHandoff?: (event: HandoffEvent) => void;
  onError?: (error: string) => void;
}

export async function sendMessageSSE(
  conversationId: string,
  data: { content: string; knowledge_base_id?: string },
  callbacks: StreamCallbacks,
): Promise<void> {
  const headers = new Headers({ "Content-Type": "application/json" });
  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${API_URL}/conversations/${conversationId}/messages`, {
    method: "POST",
    headers,
    body: JSON.stringify(data),
  });

  if (res.status === 401) {
    await res.body?.cancel();
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return sendMessageSSE(conversationId, data, callbacks);
    }
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Stream failed ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "";
  let dataLines: string[] = [];
  let finished = false;

  const dispatchEvent = () => {
    if (!currentEvent && dataLines.length === 0) {
      return;
    }

    const eventName = currentEvent;
    // A token may contain newlines. sse-starlette encodes each line as a
    // separate `data:` field, so join them back to preserve formatting.
    const data = dataLines.join("\n");
    currentEvent = "";
    dataLines = [];

    if (eventName === "done" || data === "[DONE]") {
      finished = true;
      callbacks.onDone();
      return;
    }
    if (eventName === "error") {
      finished = true;
      callbacks.onError?.(data);
      return;
    }
    if (eventName === "tool_call") {
      try {
        callbacks.onToolCall?.(JSON.parse(data) as ToolCallEvent);
      } catch {
        // Ignore malformed tool events; the final message still renders.
      }
      return;
    }
    if (eventName === "tool_result") {
      try {
        callbacks.onToolResult?.(JSON.parse(data) as ToolResultEvent);
      } catch {
        // Ignore malformed tool events; the final message still renders.
      }
      return;
    }
    if (eventName === "handoff") {
      try {
        callbacks.onHandoff?.(JSON.parse(data) as HandoffEvent);
      } catch {
        // Ignore malformed handoff events; polling will update the status.
      }
      return;
    }
    if (eventName && eventName !== "token") {
      // Unknown event type: keep it out of the token stream.
      return;
    }
    if (data) {
      callbacks.onToken(data);
    }
  };

  const processLine = (rawLine: string) => {
    const line = rawLine.endsWith("\r") ? rawLine.slice(0, -1) : rawLine;
    if (line === "") {
      dispatchEvent();
      return;
    }
    if (line.startsWith(":")) {
      // SSE comment / keep-alive ping.
      return;
    }

    const colonIndex = line.indexOf(":");
    const field = colonIndex === -1 ? line : line.slice(0, colonIndex);
    let value = colonIndex === -1 ? "" : line.slice(colonIndex + 1);
    if (value.startsWith(" ")) {
      value = value.slice(1);
    }

    if (field === "event") {
      currentEvent = value;
    } else if (field === "data") {
      dataLines.push(value);
    }
  };

  while (!finished) {
    const { done, value } = await reader.read();
    if (done) {
      buffer += decoder.decode();
      if (buffer.length > 0) {
        processLine(buffer);
        buffer = "";
      }
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    let newlineIndex = buffer.indexOf("\n");
    while (!finished && newlineIndex !== -1) {
      processLine(buffer.slice(0, newlineIndex));
      buffer = buffer.slice(newlineIndex + 1);
      newlineIndex = buffer.indexOf("\n");
    }
  }

  if (!finished) {
    dispatchEvent();
    callbacks.onDone();
  }
}

export function getStats() {
  return apiFetch<Stats>("/stats");
}

export function apiLogin(data: { username: string; password: string }) {
  return apiFetch<AuthPayload>("/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function apiRegister(data: { username: string; email: string; password: string }) {
  return apiFetch<AuthPayload>("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function apiRefresh(data: { refresh_token: string }) {
  return apiFetch<{ access_token: string; token_type: string }>("/auth/refresh", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function apiGetMe() {
  return apiFetch<User>("/auth/me");
}

export function apiChangePassword(data: { current_password: string; new_password: string }) {
  return apiFetch<{ ok: boolean }>("/auth/change-password", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function listUsers(params?: { search?: string; role?: string }) {
  const searchParams = new URLSearchParams();
  if (params?.search) searchParams.set("search", params.search);
  if (params?.role) searchParams.set("role", params.role);
  const query = searchParams.toString();
  return apiFetch<User[]>(`/users${query ? `?${query}` : ""}`);
}

export function createUser(data: {
  username: string;
  email: string;
  password: string;
  role: "admin" | "staff" | "user";
  is_active?: boolean;
}) {
  return apiFetch<User>("/users", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateUser(
  userId: string,
  data: Partial<Pick<User, "username" | "email" | "role" | "is_active">>,
) {
  return apiFetch<User>(`/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteUser(userId: string) {
  return apiFetch<void>(`/users/${userId}`, { method: "DELETE" });
}

export function resetUserPassword(userId: string, data: { new_password: string }) {
  return apiFetch<{ ok: boolean }>(`/users/${userId}/reset-password`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export type SupportScope = "waiting" | "mine" | "active" | "closed" | "all";

export function listSupportConversations(scope: SupportScope, search?: string) {
  const params = new URLSearchParams({ scope });
  if (search?.trim()) params.set("search", search.trim());
  return apiFetch<SupportConversation[]>(
    `/support/conversations?${params.toString()}`,
  );
}

export function getSupportConversation(id: string) {
  return apiFetch<SupportConversationDetail>(`/support/conversations/${id}`);
}

export function claimSupportConversation(id: string) {
  return apiFetch<SupportAction>(`/support/conversations/${id}/claim`, {
    method: "POST",
  });
}

export function assignSupportConversation(id: string, staffId: string | null) {
  return apiFetch<SupportAction>(`/support/conversations/${id}/assign`, {
    method: "POST",
    body: JSON.stringify({ staff_id: staffId }),
  });
}

export function sendSupportMessage(
  id: string,
  data: { content: string; is_internal: boolean },
) {
  return apiFetch<SupportMessageResult>(
    `/support/conversations/${id}/messages`,
    {
      method: "POST",
      body: JSON.stringify(data),
    },
  );
}

export function refreshSupportSummary(id: string) {
  return apiFetch<SupportConversation>(
    `/support/conversations/${id}/summary`,
    { method: "POST" },
  );
}

export function returnSupportToBot(id: string) {
  return apiFetch<SupportAction>(
    `/support/conversations/${id}/return-to-bot`,
    { method: "POST" },
  );
}

export function getSupportStats() {
  return apiFetch<SupportStats>("/support/stats");
}

export function listSupportStaff() {
  return apiFetch<SupportStaffOption[]>("/support/staff");
}
