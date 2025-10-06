import React, { useRef } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Label } from './ui/label';
import { ScrollArea } from './ui/scroll-area';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from './ui/sheet';
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from './ui/select';
import { cn } from '../lib/utils';
import MessageBubble from './MessageBubble';
import ModelSettings from './ModelSettings';
import { FiPlus, FiSettings, FiUpload, FiTrash2, FiDownload } from 'react-icons/fi';

const API_URL = 'http://localhost:5001/api';

export default function RevampLayout({
  // state
  documents,
  selectedDocument,
  messages,
  loading,
  chatMode,
  modelSettings,
  savedConversations,
  // actions
  onSelectDocument,
  onUpload,
  onClearDocuments,
  onSendMessage,
  onToggleMode,
  onNewChat,
  onUpdateModelSettings,
  onLoadConversation,
  onDeleteConversation,
  onExportConversation,
  onExportAllConversations,
  onImportConversations,
}) {
  const [input, setInput] = React.useState('');
  const fileRef = useRef();
  const importRef = useRef();

  const handleSend = (e) => {
    e?.preventDefault();
    if (!loading && input.trim()) {
      onSendMessage(input);
      setInput('');
    }
  };

  return (
    <div className="h-full grid grid-rows-[auto_1fr]">
      {/* Top Nav */}
      <div className="border-b bg-card">
        <div className="mx-auto max-w-7xl px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-md bg-primary" />
            <div className="text-xl font-semibold">DocQueryAI</div>
            <div className="ml-4 text-sm text-muted-foreground hidden sm:block">
              {chatMode === 'document' ? 'Document mode' : 'General chat'}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={onToggleMode}>
              {chatMode === 'document' ? 'Use General' : 'Use Document'}
            </Button>
            <Button onClick={onNewChat} variant="secondary">
              <FiPlus className="mr-2" /> New Chat
            </Button>
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="outline"><FiSettings className="mr-2" /> Model</Button>
              </SheetTrigger>
              <SheetContent side="right">
                <SheetHeader>
                  <SheetTitle>Model Settings</SheetTitle>
                </SheetHeader>
                <div className="mt-4">
                  {/* Reuse existing settings component */}
                  <ModelSettings currentSettings={modelSettings} onSave={onUpdateModelSettings} />
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="grid grid-cols-1 md:grid-cols-[340px_1fr] overflow-hidden">
        {/* Sidebar */}
        <div className="border-r bg-background">
          <div className="h-full flex flex-col">
            <div className="p-4 border-b">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Upload Document</CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex items-center gap-2">
                    <input ref={fileRef} type="file" className="hidden" accept=".pdf,.txt" onChange={(e)=>e.target.files[0] && onUpload(e.target.files[0])} />
                    <Button onClick={() => fileRef.current?.click()} disabled={loading}>
                      <FiUpload className="mr-2" /> {loading ? 'Uploading...' : 'Choose File'}
                    </Button>
                    <Button variant="outline" onClick={onClearDocuments} disabled={!documents.length}>
                      <FiTrash2 className="mr-2" /> Clear All
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
            <div className="px-4 pt-4 text-sm text-muted-foreground">Documents</div>
            <ScrollArea className="flex-1 px-4 pb-4">
              <div className="space-y-2">
                {documents.length === 0 ? (
                  <div className="text-sm text-muted-foreground px-2">No documents uploaded.</div>
                ) : (
                  documents.map((doc) => (
                    <button key={doc.name} onClick={() => onSelectDocument(doc.name)} className={cn(
                      "w-full text-left p-3 rounded-md border hover:bg-accent hover:text-accent-foreground",
                      selectedDocument === doc.name && "border-primary"
                    )}>
                      <div className="font-medium truncate">{doc.name}</div>
                      <div className="text-xs text-muted-foreground truncate">{doc.excerpt}</div>
                    </button>
                  ))
                )}
              </div>
            </ScrollArea>

            <div className="px-4 py-3 border-t">
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm text-muted-foreground">Saved Chats</div>
                <div className="flex items-center gap-2">
                  <input ref={importRef} className="hidden" type="file" accept=".json" onChange={onImportConversations} />
                  <Button variant="outline" size="sm" onClick={() => importRef.current?.click()}>Import</Button>
                  <Button variant="outline" size="sm" onClick={onExportAllConversations} disabled={!savedConversations.length}><FiDownload className="mr-2" />Export</Button>
                </div>
              </div>
              <ScrollArea className="h-40">
                <div className="space-y-2">
                  {savedConversations.length === 0 ? (
                    <div className="text-xs text-muted-foreground px-2">No saved conversations.</div>
                  ) : (
                    savedConversations.map((conv) => (
                      <div key={conv.id} className="flex items-center justify-between gap-2 p-2 rounded-md border">
                        <button className="flex-1 text-left" onClick={() => onLoadConversation(conv)}>
                          <div className="text-sm font-medium truncate">{conv.title}</div>
                          <div className="text-[11px] text-muted-foreground">{new Date(conv.timestamp).toLocaleString()}</div>
                        </button>
                        <div className="flex items-center gap-2">
                          <Button variant="outline" size="sm" onClick={()=>onExportConversation(conv)}><FiDownload /></Button>
                          <Button variant="destructive" size="sm" onClick={()=>onDeleteConversation(conv.id)}><FiTrash2 /></Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </ScrollArea>
            </div>
          </div>
        </div>

        {/* Chat area */}
        <div className="h-full">
          <div className="h-full grid grid-rows-[1fr_auto]">
            <ScrollArea className="p-4">
              <div className="max-w-3xl mx-auto space-y-3">
                {messages.map((m) => (
                  <Card key={m.id} className={cn("border", m.sender === 'user' ? 'bg-white' : 'bg-muted/30')}>
                    <CardContent className="p-4">
                      <MessageBubble message={m.text} sender={m.sender} streaming={m.streaming} />
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
            <form onSubmit={handleSend} className="border-t bg-background p-4">
              <div className="max-w-3xl mx-auto flex gap-2">
                <Textarea
                  value={input}
                  onChange={(e)=>setInput(e.target.value)}
                  placeholder={chatMode === 'document' ? 'Ask about your document…' : 'Ask anything…'}
                  className="min-h-[56px]"
                />
                <Button type="submit" disabled={loading || !input.trim()}>Send</Button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

