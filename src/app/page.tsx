'use client';

import { ChatInterface } from '@/components/ChatInterface';
import { useChat } from '@/hooks/useChat';

export default function Home() {
  const chat = useChat();

  return (
    <ChatInterface
      messages={chat.messages}
      sessionId={chat.sessionId}
      isLoading={chat.isLoading}
      currentStep={chat.currentStep}
      responseType={chat.responseType}
      fields={chat.fields}
      options={chat.options}
      isDone={chat.isDone}
      onSendMessage={chat.sendMessage}
      onFormSubmit={chat.submitForm}
    />
  );
}
