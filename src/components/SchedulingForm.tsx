'use client';

import React, { useState } from 'react';
import { FieldDescriptor } from '@/types/chat';

interface SchedulingFormProps {
  fields: FieldDescriptor[];
  onSubmit: (data: Record<string, unknown>) => void;
}

export const SchedulingForm: React.FC<SchedulingFormProps> = ({
  fields,
  onSubmit,
}) => {
  const [selections, setSelections] = useState<Record<string, string[]>>({});

  const handleToggle = (fieldName: string, option: string) => {
    setSelections((prev) => {
      const current = prev[fieldName] || [];
      if (current.includes(option)) {
        return { ...prev, [fieldName]: current.filter((o) => o !== option) };
      } else {
        return { ...prev, [fieldName]: [...current, option] };
      }
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Check at least one option selected per field
    const allHaveSelections = fields.every(
      (field) => (selections[field.name] || []).length > 0
    );
    if (allHaveSelections) {
      onSubmit(selections);
    }
  };

  const isValid = fields.every(
    (field) => (selections[field.name] || []).length > 0
  );

  return (
    <div className="w-full max-w-md mx-auto px-4 mb-6">
      <form
        onSubmit={handleSubmit}
        className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm"
      >
        {fields.map((field) => (
          <div key={field.name} className="mb-6 last:mb-0">
            <label className="block text-sm font-medium text-gray-700 mb-3">
              {field.label}
            </label>
            <div className="space-y-2">
              {field.options?.map((option) => {
                const isSelected = (selections[field.name] || []).includes(
                  option
                );
                return (
                  <label
                    key={option}
                    className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-all ${
                      isSelected
                        ? 'border-rrc-blue bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => handleToggle(field.name, option)}
                      className="w-4 h-4 text-rrc-blue rounded focus:ring-rrc-blue"
                    />
                    <span className="text-gray-900 text-sm">{option}</span>
                  </label>
                );
              })}
            </div>
          </div>
        ))}

        <button
          type="submit"
          disabled={!isValid}
          className="w-full mt-4 px-4 py-3 bg-rrc-blue text-white rounded-lg font-medium hover:bg-rrc-blue-dark transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          Submit
        </button>
      </form>
    </div>
  );
};
