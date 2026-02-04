export interface FieldDescriptor {
  name: string;
  type: string;  // "text" | "email" | "tel" | "date" | "number" | "select" | "multi_select"
  label: string;
  options?: string[];
}

export interface ChatResponse {
  session_id: string;
  message: string;
  type: "text" | "form" | "end";
  step: string;
  field: string | null;
  fields: FieldDescriptor[] | null;
  options: string[] | null;
  done: boolean;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export interface SessionRequest {
  study_id: string;
}

export interface ChatRequest {
  session_id: string;
  message: string;
}
