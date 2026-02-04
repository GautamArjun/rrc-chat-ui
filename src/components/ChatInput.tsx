'use client';

import React, { useState, KeyboardEvent } from 'react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  type?: 'text' | 'password';
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  disabled = false,
  placeholder = 'Type your message...',
  type = 'text',
}) => {
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex gap-3">
      <input
        type={type}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        className="flex-1 px-4 py-3 border border-gray-300 rounded-rrc focus:outline-none focus:ring-2 focus:ring-rrc-accent focus:border-rrc-accent disabled:bg-gray-100 disabled:cursor-not-allowed text-rrc-primary"
      />
      <button
        onClick={handleSend}
        disabled={disabled || !input.trim()}
        className="px-6 py-3 bg-rrc-accent text-white rounded-rrc font-semibold hover:bg-rrc-accent-dark transition-colors disabled:bg-rrc-muted disabled:cursor-not-allowed"
      >
        Send
      </button>
    </div>
  );
};
