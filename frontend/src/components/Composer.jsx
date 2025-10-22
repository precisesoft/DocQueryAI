import React, { useEffect, useRef, useState } from 'react';
import { Paperclip, Send } from 'lucide-react';
import { cn } from '../lib/utils';

function Composer({
  value,
  onChange,
  onSubmit,
  onUpload,
  loading = false,
  compact = false,
  placeholder = 'Ask anything… (Enter to send, Shift+Enter for newline)'
}) {
  const fileRef = useRef();
  const textRef = useRef();
  const [singleLine, setSingleLine] = useState(true);

  useEffect(() => {
    if (!textRef.current) return;
    const el = textRef.current;
    el.style.height = 'auto';
    const max = 160;
    const measured = Math.min(el.scrollHeight, max);
    const isSingle = measured <= 44;
    setSingleLine(isSingle);
    el.style.height = (isSingle ? 44 : measured) + 'px';
  }, [value]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSubmit?.();
    }
  };

  const pickFile = () => fileRef.current?.click();
  const handleFile = (e) => {
    const file = e.target.files?.[0];
    if (file && onUpload) onUpload(file);
    e.target.value = null;
  };

  return (
    <div className="bg-background">
      <div className="w-full max-w-3xl mx-auto px-3 py-2">
        <div className={cn(
          'relative flex items-center gap-2 rounded-2xl border bg-card/80 backdrop-blur px-2 sm:px-3 py-2 shadow-sm',
          loading && 'opacity-90'
        )}>
          <input ref={fileRef} type="file" className="hidden" accept=".pdf,.txt" onChange={handleFile} />
          <button
            type="button"
            onClick={pickFile}
            disabled={loading}
            className="p-2 rounded-md hover:bg-accent text-muted-foreground"
            title="Attach document"
          >
            <Paperclip className="h-5 w-5" />
          </button>
          

          <textarea
            ref={textRef}
            value={value}
            onChange={(e)=>onChange?.(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder={placeholder}
            disabled={loading}
            className={cn(
              'flex-1 bg-transparent outline-none resize-none text-sm placeholder:text-muted-foreground text-left',
              'min-h-[44px] max-h-40 px-1',
              singleLine ? 'leading-[44px] py-0' : 'leading-[1.35] py-1'
            )}
          />

          <div className="ml-auto flex items-center gap-1 sm:gap-2">
            <button
              type="button"
              onClick={onSubmit}
              disabled={loading || !value.trim()}
              className={cn('p-2 rounded-md',
                value.trim() ? 'bg-primary text-primary-foreground hover:opacity-90' : 'bg-secondary text-secondary-foreground opacity-60 cursor-not-allowed'
              )}
              title="Send"
            >
              <Send className="h-5 w-5" />
            </button>
          </div>
        </div>
        <div className="px-1 pt-1 text-[11px] text-muted-foreground select-none">Enter to send • Shift+Enter for newline</div>
      </div>
    </div>
  );
}

export default Composer;
