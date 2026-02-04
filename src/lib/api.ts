import { ChatResponse, SessionRequest, ChatRequest } from '@/types/chat';

const API_BASE = '/api';

export async function createSession(studyId: string): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/session`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ study_id: studyId } as SessionRequest),
  });

  if (!response.ok) {
    throw new Error(`Failed to create session: ${response.statusText}`);
  }

  return response.json();
}

export async function sendChatMessage(
  sessionId: string,
  message: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ session_id: sessionId, message } as ChatRequest),
  });

  if (!response.ok) {
    throw new Error(`Failed to send message: ${response.statusText}`);
  }

  return response.json();
}
