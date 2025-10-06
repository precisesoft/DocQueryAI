import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import CodeBlock from './CodeBlock';

function MessageBubble({ message, sender, streaming }) {
  const [thinkingExpanded, setThinkingExpanded] = useState(false);
  const [parsedContent, setParsedContent] = useState({ thinking: '', visible: '' });

  useEffect(() => {
    if (sender === 'bot') {
      const thinkEndIndex = message.indexOf('</think>');
      if (thinkEndIndex !== -1) {
        const thinking = message.substring(0, thinkEndIndex).trim();
        const visible = message.substring(thinkEndIndex + 8).trim();
        setParsedContent({ thinking, visible });
      } else {
        setParsedContent({ thinking: '', visible: message });
      }
    } else {
      setParsedContent({ thinking: '', visible: message });
    }
  }, [message, sender]);

  return (
    <div className={sender === 'user' ? 'text-right' : 'text-left'}>
      {parsedContent.thinking && (
        <div className="mb-2">
          <button
            onClick={() => setThinkingExpanded(!thinkingExpanded)}
            className="text-xs text-muted-foreground hover:underline"
          >
            {thinkingExpanded ? 'Hide' : 'Show'} AI thinking
          </button>
          {thinkingExpanded && (
            <pre className="mt-1 whitespace-pre-wrap text-xs bg-muted p-2 rounded-md">{parsedContent.thinking}</pre>
          )}
        </div>
      )}
      <div className="prose prose-sm dark:prose-invert max-w-none">
        {sender === 'user' ? (
          parsedContent.visible
        ) : (
          <ReactMarkdown
            components={{
              code({node, inline, className, children, ...props}) {
                const match = /language-(\w+)/.exec(className || '');
                return !inline && match ? (
                  <CodeBlock 
                    language={match[1]} 
                    value={String(children).replace(/\n$/, '')}
                  />
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              }
            }}
          >
            {parsedContent.visible}
          </ReactMarkdown>
        )}
      </div>
      {streaming && (
        <div className="mt-1 text-xs text-muted-foreground animate-pulse">typing…</div>
      )}
    </div>
  );
}

export default MessageBubble;
