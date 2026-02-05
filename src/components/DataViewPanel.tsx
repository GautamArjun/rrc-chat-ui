'use client';

import React, { useEffect, useState, useRef } from 'react';

interface FieldGroup {
  name: string;
  fields: [string, string][];
}

interface LeadDataResponse {
  session_id: string;
  lead_id: number | null;
  current_step: string;
  lead_data: Record<string, string | null> | null;
  missing_fields: string[];
  field_groups: FieldGroup[];
}

interface DataViewPanelProps {
  sessionId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export const DataViewPanel: React.FC<DataViewPanelProps> = ({
  sessionId,
  isOpen,
  onClose,
}) => {
  const [data, setData] = useState<LeadDataResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatedFields, setUpdatedFields] = useState<Set<string>>(new Set());
  const previousDataRef = useRef<Record<string, string | null> | null>(null);

  const fetchData = async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(`/api/lead-data?session_id=${sessionId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch lead data');
      }
      const newData = await response.json();

      // Detect which fields changed
      if (previousDataRef.current && newData.lead_data) {
        const changed = new Set<string>();
        for (const [key, value] of Object.entries(newData.lead_data)) {
          const prevValue = previousDataRef.current[key];
          if (prevValue !== value && value !== null) {
            changed.add(key);
          }
        }
        if (changed.size > 0) {
          setUpdatedFields(changed);
          // Clear highlights after 2 seconds
          setTimeout(() => setUpdatedFields(new Set()), 2000);
        }
      }

      previousDataRef.current = newData.lead_data;
      setData(newData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch and polling
  useEffect(() => {
    if (!isOpen || !sessionId) return;

    setLoading(true);
    fetchData();

    // Poll every 2 seconds
    const interval = setInterval(fetchData, 2000);

    return () => clearInterval(interval);
  }, [isOpen, sessionId]);

  if (!isOpen) return null;

  const getFieldStatus = (fieldName: string, value: string | null | undefined) => {
    const isMissing = data?.missing_fields?.includes(fieldName);
    const hasValue = value !== null && value !== undefined && value !== '';
    const isUpdated = updatedFields.has(fieldName);

    return { isMissing, hasValue, isUpdated };
  };

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-white shadow-2xl border-l border-gray-200 z-50 flex flex-col">
      {/* Header */}
      <div className="bg-rrc-primary text-white px-4 py-3 flex items-center justify-between">
        <div>
          <h2 className="font-semibold">Lead Data View</h2>
          <p className="text-xs text-rrc-muted">
            {data?.lead_id ? `Lead #${data.lead_id}` : 'No lead yet'}
          </p>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-rrc-primary-light rounded transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Current Step */}
      <div className="px-4 py-2 bg-rrc-bg border-b border-gray-200">
        <span className="text-xs font-medium text-rrc-primary">Current Step: </span>
        <span className="text-xs text-rrc-accent font-mono">{data?.current_step || 'loading...'}</span>
      </div>

      {/* Legend */}
      <div className="px-4 py-2 border-b border-gray-200 flex gap-4 text-xs">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 bg-green-500 rounded-full"></span> Has value
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 bg-gray-300 rounded-full"></span> Missing
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 bg-rrc-accent rounded-full animate-pulse"></span> Just updated
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading && !data && (
          <div className="text-center text-gray-500 py-8">Loading...</div>
        )}

        {error && (
          <div className="text-center text-red-500 py-8">{error}</div>
        )}

        {!data?.lead_data && !loading && (
          <div className="text-center text-gray-500 py-8">
            <p className="mb-2">No lead record yet</p>
            <p className="text-xs">Complete the identity form to create a lead</p>
          </div>
        )}

        {data?.field_groups && (
          <div className="space-y-4">
            {data.field_groups.map((group) => (
              <div key={group.name} className="border border-gray-200 rounded-rrc overflow-hidden">
                <div className="bg-gray-50 px-3 py-2 border-b border-gray-200">
                  <h3 className="text-sm font-semibold text-rrc-primary">{group.name}</h3>
                </div>
                <div className="divide-y divide-gray-100">
                  {group.fields.map(([fieldName, label]) => {
                    const value = data.lead_data?.[fieldName];
                    const { hasValue, isMissing, isUpdated } = getFieldStatus(fieldName, value);

                    return (
                      <div
                        key={fieldName}
                        className={`px-3 py-2 flex items-center justify-between transition-all duration-300 ${
                          isUpdated ? 'bg-blue-50' : ''
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span
                            className={`w-2 h-2 rounded-full flex-shrink-0 ${
                              isUpdated
                                ? 'bg-rrc-accent animate-pulse'
                                : hasValue
                                ? 'bg-green-500'
                                : 'bg-gray-300'
                            }`}
                          ></span>
                          <span className="text-xs text-gray-600">{label}</span>
                        </div>
                        <span
                          className={`text-xs font-mono truncate max-w-[180px] ${
                            hasValue ? 'text-rrc-primary' : 'text-gray-400'
                          }`}
                          title={value || ''}
                        >
                          {hasValue ? value : '—'}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 text-xs text-gray-500 text-center">
        Auto-refreshing every 2 seconds
      </div>
    </div>
  );
};
