'use client';

import React, { useRef, useEffect, useState } from 'react';
import Image from 'next/image';
import { Message, FieldDescriptor } from '@/types/chat';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { TypingIndicator } from './TypingIndicator';
import { IdentityForm } from './IdentityForm';
import { ProfileForm } from './ProfileForm';
import { PrescreenForm } from './PrescreenForm';
import { SchedulingForm } from './SchedulingForm';
import { DataViewPanel } from './DataViewPanel';

interface ChatInterfaceProps {
  messages: Message[];
  sessionId: string | null;
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
  sessionId,
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
  const [isDataViewOpen, setIsDataViewOpen] = useState(false);

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
    <div className="flex flex-col min-h-screen bg-rrc-bg">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-white shadow-md border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Image
              src="/rrc-logo.png"
              alt="Rose Research Center"
              width={180}
              height={40}
              className="h-10 w-auto"
              priority
            />
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden sm:block text-sm text-rrc-primary font-medium bg-rrc-bg px-3 py-1.5 rounded-full border border-gray-200">
              ZYN Nicotine Pouch Study
            </span>
            <button
              onClick={() => setIsDataViewOpen(!isDataViewOpen)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-rrc text-sm font-medium transition-colors ${
                isDataViewOpen
                  ? 'bg-rrc-accent text-white'
                  : 'bg-rrc-bg text-rrc-primary border border-gray-200 hover:bg-gray-100'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2 1 3 3 3h10c2 0 3-1 3-3V7c0-2-1-3-3-3H7C5 4 4 5 4 7z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 12h16" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16" />
              </svg>
              <span className="hidden sm:inline">Data View</span>
            </button>
          </div>
        </div>
      </header>

      {/* Data View Panel */}
      <DataViewPanel
        sessionId={sessionId}
        isOpen={isDataViewOpen}
        onClose={() => setIsDataViewOpen(false)}
      />

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
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4 shadow-lg">
          <div className="max-w-3xl mx-auto">
            <ChatInput onSend={onSendMessage} disabled={isLoading} />
          </div>
        </div>
      )}

      {/* Done state */}
      {isDone && (
        <div className="fixed bottom-0 left-0 right-0 bg-rrc-primary p-4">
          <div className="max-w-3xl mx-auto text-center text-white">
            This conversation has ended. Thank you for your time.
          </div>
        </div>
      )}
    </div>
  );
};
