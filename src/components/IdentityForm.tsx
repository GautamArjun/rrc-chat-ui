'use client';

import React, { useState } from 'react';

interface IdentityFormProps {
  onSubmit: (data: Record<string, unknown>) => void;
}

export const IdentityForm: React.FC<IdentityFormProps> = ({ onSubmit }) => {
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email && phone) {
      onSubmit({ email, phone });
    }
  };

  const formatPhone = (value: string) => {
    // Remove non-digits
    const digits = value.replace(/\D/g, '');
    // Format as XXX-XXX-XXXX
    if (digits.length <= 3) return digits;
    if (digits.length <= 6) return `${digits.slice(0, 3)}-${digits.slice(3)}`;
    return `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6, 10)}`;
  };

  return (
    <div className="w-full max-w-md mx-auto px-4 mb-6">
      <form
        onSubmit={handleSubmit}
        className="bg-white border border-gray-200 rounded-rrc p-6 shadow-sm"
      >
        <h3 className="text-lg font-semibold text-rrc-primary mb-4">
          Contact Information
        </h3>

        <div className="space-y-4">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-rrc-primary mb-1"
            >
              Email Address
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-rrc focus:outline-none focus:ring-2 focus:ring-rrc-accent focus:border-rrc-accent text-rrc-primary"
            />
          </div>

          <div>
            <label
              htmlFor="phone"
              className="block text-sm font-medium text-rrc-primary mb-1"
            >
              Phone Number
            </label>
            <input
              type="tel"
              id="phone"
              value={phone}
              onChange={(e) => setPhone(formatPhone(e.target.value))}
              placeholder="919-555-0100"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-rrc focus:outline-none focus:ring-2 focus:ring-rrc-accent focus:border-rrc-accent text-rrc-primary"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={!email || !phone}
          className="w-full mt-6 px-4 py-3 bg-rrc-accent text-white rounded-rrc font-semibold hover:bg-rrc-accent-dark transition-colors disabled:bg-rrc-muted disabled:cursor-not-allowed"
        >
          Continue
        </button>
      </form>
    </div>
  );
};
