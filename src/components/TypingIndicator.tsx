'use client';

import React from 'react';

export const TypingIndicator: React.FC = () => {
  return (
    <div className="flex gap-3 mb-4 px-4">
      {/* Avatar */}
      <div className="w-8 h-8 rounded-lg bg-rrc-primary flex-shrink-0 flex items-center justify-center">
        <span className="text-white font-semibold text-xs">RRC</span>
      </div>

      {/* Typing dots */}
      <div className="bg-white border border-gray-200 px-4 py-3 rounded-rrc rounded-tl-none shadow-sm">
        <div className="flex gap-1">
          <div className="w-2 h-2 bg-rrc-muted rounded-full typing-dot" />
          <div className="w-2 h-2 bg-rrc-muted rounded-full typing-dot" />
          <div className="w-2 h-2 bg-rrc-muted rounded-full typing-dot" />
        </div>
      </div>
    </div>
  );
};
