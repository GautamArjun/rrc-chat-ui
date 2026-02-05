import { useState, useCallback, useEffect } from 'react';
import { Message, ChatResponse, FieldDescriptor } from '@/types/chat';
import { createSession, sendChatMessage } from '@/lib/api';

const STUDY_ID = 'zyn';

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState<string>('');
  const [responseType, setResponseType] = useState<'text' | 'form' | 'end'>('text');
  const [fields, setFields] = useState<FieldDescriptor[] | null>(null);
  const [options, setOptions] = useState<string[] | null>(null);
  const [isDone, setIsDone] = useState(false);

  const addMessage = useCallback((role: 'user' | 'assistant', content: string) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      role,
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, newMessage]);
  }, []);

  const handleResponse = useCallback((response: ChatResponse) => {
    setSessionId(response.session_id);
    setCurrentStep(response.step);
    setResponseType(response.type);
    setFields(response.fields);
    setOptions(response.options);
    setIsDone(response.done);

    if (response.message) {
      addMessage('assistant', response.message);
    }
  }, [addMessage]);

  // Initialize session on mount
  useEffect(() => {
    const initSession = async () => {
      setIsLoading(true);
      try {
        const response = await createSession(STUDY_ID);
        handleResponse(response);
      } catch (error) {
        console.error('Failed to initialize session:', error);
        addMessage('assistant', 'Sorry, there was an error connecting. Please refresh the page to try again.');
      } finally {
        setIsLoading(false);
      }
    };

    initSession();
  }, [addMessage, handleResponse]);

  const sendMessage = useCallback(async (content: string) => {
    if (!sessionId || isLoading || isDone) return;

    addMessage('user', content);
    setIsLoading(true);

    try {
      const response = await sendChatMessage(sessionId, content);
      handleResponse(response);
    } catch (error) {
      console.error('Failed to send message:', error);
      addMessage('assistant', 'Sorry, there was an error. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, isLoading, isDone, addMessage, handleResponse]);

  const submitForm = useCallback(async (formData: Record<string, unknown>) => {
    if (!sessionId || isLoading || isDone) return;

    const jsonMessage = JSON.stringify(formData);

    // Show user-friendly version of what was submitted
    const displayMessage = Object.entries(formData)
      .map(([key, value]) => {
        if (Array.isArray(value)) {
          return `${key}: ${value.join(', ')}`;
        }
        return `${key}: ${value}`;
      })
      .join('\n');

    addMessage('user', displayMessage || jsonMessage);
    setIsLoading(true);

    try {
      const response = await sendChatMessage(sessionId, jsonMessage);
      handleResponse(response);
    } catch (error) {
      console.error('Failed to submit form:', error);
      addMessage('assistant', 'Sorry, there was an error. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, isLoading, isDone, addMessage, handleResponse]);

  return {
    messages,
    sessionId,
    isLoading,
    currentStep,
    responseType,
    fields,
    options,
    isDone,
    sendMessage,
    submitForm,
  };
}
