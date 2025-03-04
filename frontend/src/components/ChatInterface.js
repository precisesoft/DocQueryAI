import React, { useState, useRef, useEffect } from 'react';
import { FiSend, FiSave, FiChevronsDown } from 'react-icons/fi';
import MessageBubble from './MessageBubble';
import ModelSettings from './ModelSettings';

// Add a small indicator to show if document mode is active
function ChatInterface({ 
  messages, 
  onSendMessage, 
  loading, 
  chatMode, 
  onToggleMode,
  onSaveConversation,
  onNewChat,
  modelSettings,
  onUpdateModelSettings
}) {
  const [input, setInput] = useState('');
  const endOfMessagesRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const inputRef = useRef(null);
  const [showScrollButton, setShowScrollButton] = useState(false);

  // Improved scroll to bottom when messages change
  useEffect(() => {
    const scrollToBottom = () => {
      if (endOfMessagesRef.current) {
        // Use a small timeout to ensure DOM is updated
        setTimeout(() => {
          endOfMessagesRef.current.scrollIntoView({ 
            behavior: 'smooth',
            block: 'end'
          });
        }, 100);
      }
    };
    
    scrollToBottom();
    
    // Also add event listener for window resize to maintain scroll position
    window.addEventListener('resize', scrollToBottom);
    return () => window.removeEventListener('resize', scrollToBottom);
  }, [messages]);

  // Add this useEffect to ensure proper container size
  useEffect(() => {
    const updateContainerHeight = () => {
      if (messagesContainerRef.current) {
        // Ensure the container takes the available space
        const headerHeight = document.querySelector('.chat-header')?.offsetHeight || 0;
        const inputHeight = document.querySelector('.input-area')?.offsetHeight || 0;
        const viewportHeight = window.innerHeight;
        
        // Calculate available space
        const availableHeight = viewportHeight - headerHeight - inputHeight;
        messagesContainerRef.current.style.height = `${availableHeight}px`;
      }
    };
    
    updateContainerHeight();
    window.addEventListener('resize', updateContainerHeight);
    
    return () => window.removeEventListener('resize', updateContainerHeight);
  }, []);

  // Add this useEffect to detect when to show the scroll button
  useEffect(() => {
    const handleScroll = () => {
      if (messagesContainerRef.current) {
        const { scrollTop, scrollHeight, clientHeight } = messagesContainerRef.current;
        // Show button when scrolled up more than 300px from bottom
        setShowScrollButton(scrollHeight - scrollTop - clientHeight > 300);
      }
    };
    
    const container = messagesContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, []);

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

  // Add a function to handle manual scrolling
  const scrollToBottom = () => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
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
        
        <div className="header-actions">
          <ModelSettings
            currentSettings={modelSettings}
            onSave={onUpdateModelSettings}
          />
          
          <button 
            className="new-chat-button"
            onClick={onNewChat}
            title="Start a new chat"
          >
            New Chat
          </button>
          
          <button 
            className="save-button"
            onClick={onSaveConversation}
            title="Save conversation"
            disabled={messages.length <= 1}
          >
            <FiSave /> Save Chat
          </button>
        </div>
      </div>
      
      <div className="messages-container" ref={messagesContainerRef}>
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
        {showScrollButton && (
          <button className="scroll-bottom-button" onClick={scrollToBottom} title="Scroll to bottom">
            <FiChevronsDown />
          </button>
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