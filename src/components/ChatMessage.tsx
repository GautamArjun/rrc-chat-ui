'use client';

import React from 'react';
import { Message } from '@/types/chat';

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div
      className={`flex gap-3 mb-4 px-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${
          isUser ? 'bg-gray-200' : 'bg-rrc-blue'
        }`}
      >
        {isUser ? (
          <svg
            className="w-4 h-4 text-gray-600"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
              clipRule="evenodd"
            />
          </svg>
        ) : (
          <span className="text-white font-semibold text-sm">R</span>
        )}
      </div>

      {/* Message bubble */}
      <div
        className={`max-w-[75%] px-4 py-3 rounded-2xl ${
          isUser
            ? 'bg-rrc-blue text-white rounded-tr-none'
            : 'bg-white border border-gray-200 rounded-tl-none shadow-sm'
        }`}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
};
