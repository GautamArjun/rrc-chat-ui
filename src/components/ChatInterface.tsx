'use client';

import React, { useRef, useEffect } from 'react';
import { Message, FieldDescriptor } from '@/types/chat';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { TypingIndicator } from './TypingIndicator';
import { IdentityForm } from './IdentityForm';
import { ProfileForm } from './ProfileForm';
import { PrescreenForm } from './PrescreenForm';
import { SchedulingForm } from './SchedulingForm';

interface ChatInterfaceProps {
  messages: Message[];
  isLoading: boolean;
  currentStep: string;
  responseType: 'text' | 'form' | 'end';
  fields: FieldDescriptor[] | null;
  options: string[] | null;
  isDone: boolean;
  onSendMessage: (content: string) => void;
  onFormSubmit: (data: Record<string, unknown>) => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  messages,
  isLoading,
  currentStep,
  responseType,
  fields,
  options,
  isDone,
  onSendMessage,
  onFormSubmit,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Determine which form to show
  const renderForm = () => {
    if (isLoading || responseType !== 'form') return null;

    // Identity form (email + phone)
    if (currentStep === 'consent_given' || currentStep === 'collecting_identity') {
      return <IdentityForm onSubmit={onFormSubmit} />;
    }

    // PIN input
    if (currentStep === 'awaiting_pin') {
      return (
        <div className="w-full max-w-md mx-auto px-4 mb-6">
          <ChatInput
            onSend={onSendMessage}
            disabled={isLoading}
            placeholder="Enter your PIN..."
            type="password"
          />
        </div>
      );
    }

    // Scheduling form (multi-select days/times)
    if (currentStep === 'scheduling' && fields) {
      return <SchedulingForm fields={fields} onSubmit={onFormSubmit} />;
    }

    // Profile form (grouped fields)
    if (currentStep.startsWith('collecting_group:') && fields) {
      return <ProfileForm fields={fields} onSubmit={onFormSubmit} />;
    }

    // Prescreen questions (yes/no options)
    if (currentStep.startsWith('prescreen:') && options) {
      return <PrescreenForm options={options} onSubmit={onSendMessage} />;
    }

    // Generic form with fields
    if (fields && fields.length > 0) {
      return <ProfileForm fields={fields} onSubmit={onFormSubmit} />;
    }

    // Generic options (radio buttons)
    if (options && options.length > 0) {
      return <PrescreenForm options={options} onSubmit={onSendMessage} />;
    }

    return null;
  };

  // Show text input only when not showing a form
  const showTextInput = responseType === 'text' && !isDone && !isLoading;

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-3xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-rrc-blue rounded-full flex items-center justify-center">
              <span className="text-white font-bold text-lg">R</span>
            </div>
            <div className="flex flex-col">
              <span className="font-semibold text-gray-900">Rose Research Center</span>
              <span className="text-xs text-gray-500">Study Screening Assistant</span>
            </div>
          </div>
          <div className="hidden sm:block">
            <span className="text-sm text-gray-500">ZYN Nicotine Pouch Study</span>
          </div>
        </div>
      </header>

      {/* Chat Area */}
      <main className="flex-1 w-full pb-32 pt-6 overflow-y-auto">
        <div className="max-w-3xl mx-auto">
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {isLoading && <TypingIndicator />}

          {/* Render form if applicable */}
          {renderForm()}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input Area */}
      {showTextInput && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4">
          <div className="max-w-3xl mx-auto">
            <ChatInput onSend={onSendMessage} disabled={isLoading} />
          </div>
        </div>
      )}

      {/* Done state */}
      {isDone && (
        <div className="fixed bottom-0 left-0 right-0 bg-gray-100 border-t border-gray-200 p-4">
          <div className="max-w-3xl mx-auto text-center text-gray-500">
            This conversation has ended. Thank you for your time.
          </div>
        </div>
      )}
    </div>
  );
};
