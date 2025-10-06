import React, { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

function CodeBlock({ language, value }) {
  const [copied, setCopied] = useState(false);
  
  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  
  return (
    <div className="relative">
      <button
        onClick={handleCopy}
        className="absolute right-2 top-2 rounded-md border bg-secondary px-2 py-1 text-xs text-secondary-foreground hover:opacity-90"
      >
        {copied ? 'Copied!' : 'Copy'}
      </button>
      <SyntaxHighlighter language={language || 'javascript'} style={atomDark}>
        {value}
      </SyntaxHighlighter>
    </div>
  );
}

export default CodeBlock;
