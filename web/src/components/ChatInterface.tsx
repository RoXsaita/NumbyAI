/**
 * ChatInterface - Native AI chat interface for NumbyAI
 * 
 * Provides a ChatGPT-like experience for interacting with the AI
 * to upload statements, answer questions, and process transactions
 */
import React, { useState, useRef, useEffect } from 'react';
import { apiClient } from '../lib/api-client';
import { ChatMessage } from './ChatMessage';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  type?: 'text' | 'file_upload' | 'question' | 'progress' | 'transaction_preview';
  file?: File;
  questions?: Array<{ id: string; question: string; answer?: string }>;
  progress?: { current: number; total: number; message: string };
}

export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [netFlow, setNetFlow] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleFileSelect = (file: File) => {
    setUploadedFile(file);
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'user',
      content: `Uploaded: ${file.name}`,
      type: 'file_upload',
      file,
    }]);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const file = e.dataTransfer.files[0];
    if (file && (file.name.endsWith('.csv') || file.name.endsWith('.xlsx') || file.name.endsWith('.xls'))) {
      handleFileSelect(file);
    }
  };

  const handleSend = async () => {
    if (!input.trim() && !uploadedFile) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input || 'Upload statement',
      type: uploadedFile ? 'file_upload' : 'text',
      file: uploadedFile || undefined,
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsStreaming(true);

    try {
      if (uploadedFile) {
        // Upload statement
        const netFlowValue = netFlow ? parseFloat(netFlow) : undefined;
        const result = await apiClient.uploadStatement(uploadedFile, netFlowValue);

        if (result.status === 'analysis_required') {
          // Show questions from AI analysis
          const questions = result.analysis?.questions || [];
          setMessages(prev => [...prev, {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: 'I need some information about your statement structure:',
            type: 'question',
            questions: questions.map((q: string, idx: number) => ({
              id: idx.toString(),
              question: q,
            })),
          }]);
        } else if (result.status === 'parsed') {
          // Show parsed transactions
          setMessages(prev => [...prev, {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: `Parsed ${result.transactions_count} transactions. Ready to categorize.`,
            type: 'transaction_preview',
          }]);
        }
        setUploadedFile(null);
        setNetFlow('');
      } else {
        // Regular chat message
        const response = await apiClient.sendChatMessage(input);
        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.response,
          type: 'text',
        }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        type: 'text',
      }]);
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      backgroundColor: '#f5f5f5',
    }}>
      {/* Messages area */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
      }}>
        {messages.length === 0 && (
          <div style={{
            textAlign: 'center',
            color: '#666',
            marginTop: '40px',
          }}>
            <h2>Welcome to NumbyAI</h2>
            <p>Upload a CSV bank statement to get started</p>
          </div>
        )}
        {messages.map(msg => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        {isStreaming && (
          <div style={{ color: '#666', fontStyle: 'italic' }}>Thinking...</div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div style={{
        borderTop: '1px solid #ddd',
        padding: '16px',
        backgroundColor: 'white',
      }}>
        {uploadedFile && (
          <div style={{
            marginBottom: '12px',
            padding: '12px',
            backgroundColor: '#f0f0f0',
            borderRadius: '8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span>{uploadedFile.name}</span>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <input
                type="number"
                placeholder="Net flow amount"
                value={netFlow}
                onChange={(e) => setNetFlow(e.target.value)}
                style={{
                  padding: '6px 12px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  width: '150px',
                }}
              />
              <button
                onClick={() => {
                  setUploadedFile(null);
                  setNetFlow('');
                }}
                style={{
                  padding: '6px 12px',
                  border: 'none',
                  backgroundColor: '#dc2626',
                  color: 'white',
                  borderRadius: '4px',
                  cursor: 'pointer',
                }}
              >
                Remove
              </button>
            </div>
          </div>
        )}
        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            type="file"
            ref={fileInputRef}
            accept=".csv,.xlsx,.xls"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFileSelect(file);
            }}
            style={{ display: 'none' }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            style={{
              padding: '10px 16px',
              border: '2px dashed #ddd',
              borderRadius: '8px',
              backgroundColor: 'white',
              cursor: 'pointer',
            }}
          >
            📎 Upload CSV
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Type a message..."
            style={{
              flex: 1,
              padding: '10px 16px',
              border: '1px solid #ddd',
              borderRadius: '8px',
              fontSize: '14px',
            }}
          />
          <button
            onClick={handleSend}
            disabled={isStreaming || (!input.trim() && !uploadedFile)}
            style={{
              padding: '10px 24px',
              border: 'none',
              backgroundColor: '#dc2626',
              color: 'white',
              borderRadius: '8px',
              cursor: isStreaming || (!input.trim() && !uploadedFile) ? 'not-allowed' : 'pointer',
              opacity: isStreaming || (!input.trim() && !uploadedFile) ? 0.5 : 1,
            }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};
