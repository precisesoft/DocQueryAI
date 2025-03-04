import React from 'react';

function MessageBubble({ message, sender, streaming }) {
  return (
    <div className={`message-bubble ${sender}-message`}>
      {message}
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