'use client';

import React, { useState } from 'react';

interface PrescreenFormProps {
  options: string[];
  onSubmit: (answer: string) => void;
}

export const PrescreenForm: React.FC<PrescreenFormProps> = ({
  options,
  onSubmit,
}) => {
  const [selected, setSelected] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selected) {
      onSubmit(selected);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto px-4 mb-6">
      <form
        onSubmit={handleSubmit}
        className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm"
      >
        <div className="space-y-3">
          {options.map((option) => (
            <label
              key={option}
              className={`flex items-center gap-3 p-4 border rounded-lg cursor-pointer transition-all ${
                selected === option
                  ? 'border-rrc-blue bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <input
                type="radio"
                name="prescreen"
                value={option}
                checked={selected === option}
                onChange={() => setSelected(option)}
                className="w-4 h-4 text-rrc-blue focus:ring-rrc-blue"
              />
              <span className="text-gray-900">{option}</span>
            </label>
          ))}
        </div>

        <button
          type="submit"
          disabled={!selected}
          className="w-full mt-6 px-4 py-3 bg-rrc-blue text-white rounded-lg font-medium hover:bg-rrc-blue-dark transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          Submit
        </button>
      </form>
    </div>
  );
};
