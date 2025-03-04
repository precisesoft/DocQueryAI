import React, { useState, useRef, useEffect } from 'react';
import { FiSend, FiSave } from 'react-icons/fi';
import MessageBubble from './MessageBubble';

// Add a small indicator to show if document mode is active
function ChatInterface({ 
  messages, 
  onSendMessage, 
  loading, 
  chatMode, 
  onToggleMode,
  onSaveConversation
}) {
  const [input, setInput] = useState('');
  const endOfMessagesRef = useRef(null);
  const inputRef = useRef(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when component mounts
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !loading) {
      onSendMessage(input);
      setInput('');
    }
  };

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <div className="left-section">
          <h1>AI Assistant</h1>
          <div className="mode-toggle">
            <span className={`mode-label ${chatMode === 'general' ? 'active' : ''}`}>General</span>
            <button 
              className={`toggle-button ${chatMode === 'document' ? 'active' : ''}`} 
              onClick={onToggleMode}
            >
              <div className="toggle-slider"></div>
            </button>
            <span className={`mode-label ${chatMode === 'document' ? 'active' : ''}`}>Document</span>
          </div>
        </div>
        
        <button 
          className="save-button"
          onClick={onSaveConversation}
          title="Save conversation"
          disabled={messages.length <= 1}
        >
          <FiSave /> Save Chat
        </button>
      </div>
      
      <div className="messages-container">
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message.text}
            sender={message.sender}
            streaming={message.streaming}
          />
        ))}
        {loading && (
          <div className="typing-indicator">
            <div className="dot"></div>
            <div className="dot"></div>
            <div className="dot"></div>
          </div>
        )}
        <div ref={endOfMessagesRef} />
      </div>
      
      <form onSubmit={handleSubmit} className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          disabled={loading}
          ref={inputRef}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          <FiSend />
        </button>
      </form>
    </div>
  );
}

export default ChatInterface;