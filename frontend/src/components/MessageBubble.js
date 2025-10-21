import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import CodeBlock from './CodeBlock';

function MessageBubble({ message, sender, streaming, compact = false }) {
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

  const isUser = sender === 'user';
  const containerClass = isUser ? 'justify-end' : 'justify-start';
  const bubbleClass = isUser
    ? 'bg-[#0A84FF] text-white rounded-2xl rounded-br-md'
    : 'bg-muted text-foreground rounded-2xl rounded-bl-md';

  return (
    <div className={`w-full flex ${containerClass} px-0.5`}>
      <div className="w-fit max-w-[95%] md:max-w-[80%] lg:max-w-[70%]">
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
        <div className={`${compact ? 'px-2 py-1.5' : 'px-2 py-2'} ${bubbleClass} overflow-hidden`}> 
          {isUser ? (
            <div className="whitespace-pre-wrap break-words [overflow-wrap:anywhere]">{parsedContent.visible}</div>
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none break-words [overflow-wrap:anywhere]">
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
            </div>
          )}
        </div>
        {streaming && !isUser && (
          <div className="mt-1 text-xs text-muted-foreground animate-pulse">Thinking…</div>
        )}
      </div>
    </div>
  );
}

export default MessageBubble;
