/**
 * ChatMessage - Individual message component for chat interface
 */
import React from 'react';
import type { Message } from './ChatInterface';

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      marginBottom: '16px',
    }}>
      <div style={{
        maxWidth: '70%',
        padding: '12px 16px',
        borderRadius: '12px',
        backgroundColor: isUser ? '#dc2626' : '#f0f0f0',
        color: isUser ? 'white' : '#333',
      }}>
        {message.type === 'file_upload' && message.file && (
          <div style={{ marginBottom: '8px' }}>
            <strong>📎 {message.file.name}</strong>
          </div>
        )}
        
        {message.type === 'question' && message.questions && (
          <div>
            <div style={{ marginBottom: '12px' }}>{message.content}</div>
            {message.questions.map(q => (
              <div key={q.id} style={{
                marginBottom: '8px',
                padding: '8px',
                backgroundColor: 'white',
                borderRadius: '6px',
              }}>
                <div style={{ marginBottom: '4px', fontWeight: 'bold' }}>{q.question}</div>
                <input
                  type="text"
                  placeholder="Your answer..."
                  style={{
                    width: '100%',
                    padding: '6px',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                  }}
                />
              </div>
            ))}
          </div>
        )}

        {message.type === 'progress' && message.progress && (
          <div>
            <div>{message.content}</div>
            <div style={{
              marginTop: '8px',
              fontSize: '12px',
              color: '#666',
            }}>
              {message.progress.message} ({message.progress.current}/{message.progress.total})
            </div>
          </div>
        )}

        {message.type === 'text' && (
          <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>
        )}

        {message.type === 'transaction_preview' && (
          <div>
            <div>{message.content}</div>
            <button
              style={{
                marginTop: '12px',
                padding: '8px 16px',
                backgroundColor: '#dc2626',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              Start Categorization
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
