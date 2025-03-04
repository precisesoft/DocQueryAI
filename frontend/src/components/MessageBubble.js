import React, { useState, useEffect } from 'react';

function MessageBubble({ message, sender, streaming }) {
  const [thinkingExpanded, setThinkingExpanded] = useState(false);
  const [parsedContent, setParsedContent] = useState({ thinking: '', visible: '' });
  
  // Parse message whenever it changes
  useEffect(() => {
    if (sender === 'bot') {
      const thinkEndIndex = message.indexOf('</think>');
      
      if (thinkEndIndex !== -1) {
        const thinking = message.substring(0, thinkEndIndex).trim();
        const visible = message.substring(thinkEndIndex + 8).trim(); // 8 is length of </think>
        setParsedContent({ thinking, visible });
      } else {
        // No thinking tag found, all content is visible
        setParsedContent({ thinking: '', visible: message });
      }
    } else {
      // User messages have no thinking part
      setParsedContent({ thinking: '', visible: message });
    }
  }, [message, sender]);
  
  return (
    <div className={`message-bubble ${sender}-message`}>
      {parsedContent.thinking && (
        <div className="thinking-section">
          <div 
            className="thinking-toggle" 
            onClick={() => setThinkingExpanded(!thinkingExpanded)}
          >
            {thinkingExpanded ? '▼' : '►'} Show AI Thinking
          </div>
          
          {thinkingExpanded && (
            <div className="thinking-content">
              {parsedContent.thinking}
            </div>
          )}
        </div>
      )}
      
      <div className="message-content">{parsedContent.visible}</div>
      
      {streaming && (
        <div className="typing-indicator">
          <div className="dot"></div>
          <div className="dot"></div>
          <div className="dot"></div>
        </div>
      )}
    </div>
  );
}

export default MessageBubble;