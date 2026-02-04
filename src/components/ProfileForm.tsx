'use client';

import React, { useState } from 'react';
import { FieldDescriptor } from '@/types/chat';

interface ProfileFormProps {
  fields: FieldDescriptor[];
  onSubmit: (data: Record<string, unknown>) => void;
}

export const ProfileForm: React.FC<ProfileFormProps> = ({ fields, onSubmit }) => {
  const [formData, setFormData] = useState<Record<string, string>>({});

  const handleChange = (name: string, value: string) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Check all required fields are filled
    const allFilled = fields.every((field) => formData[field.name]?.trim());
    if (allFilled) {
      onSubmit(formData);
    }
  };

  const renderField = (field: FieldDescriptor) => {
    const value = formData[field.name] || '';

    if (field.type === 'select' && field.options) {
      return (
        <select
          id={field.name}
          value={value}
          onChange={(e) => handleChange(field.name, e.target.value)}
          required
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-rrc-blue focus:border-transparent bg-white"
        >
          <option value="">Select...</option>
          {field.options.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      );
    }

    const inputType =
      field.type === 'number'
        ? 'number'
        : field.type === 'date'
        ? 'date'
        : field.type === 'email'
        ? 'email'
        : field.type === 'tel'
        ? 'tel'
        : 'text';

    return (
      <input
        type={inputType}
        id={field.name}
        value={value}
        onChange={(e) => handleChange(field.name, e.target.value)}
        required
        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-rrc-blue focus:border-transparent"
      />
    );
  };

  const isValid = fields.every((field) => formData[field.name]?.trim());

  return (
    <div className="w-full max-w-md mx-auto px-4 mb-6">
      <form
        onSubmit={handleSubmit}
        className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm"
      >
        <div className="space-y-4">
          {fields.map((field) => (
            <div key={field.name}>
              <label
                htmlFor={field.name}
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                {field.label}
              </label>
              {renderField(field)}
            </div>
          ))}
        </div>

        <button
          type="submit"
          disabled={!isValid}
          className="w-full mt-6 px-4 py-3 bg-rrc-blue text-white rounded-lg font-medium hover:bg-rrc-blue-dark transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          Submit
        </button>
      </form>
    </div>
  );
};
