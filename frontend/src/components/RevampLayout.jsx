import React, { useRef } from 'react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from './ui/card';
import { ScrollArea } from './ui/scroll-area';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from './ui/sheet';
import { cn } from '../lib/utils';
import MessageBubble from './MessageBubble';
import ModelSettings from './ModelSettings';
import { FiUpload, FiTrash2, FiDownload } from 'react-icons/fi';
import { Moon, Sun, MessageSquare, FileText, Settings, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from './ui/tooltip';
import { Switch } from './ui/switch';
import { Separator } from './ui/separator';

export default function RevampLayout({
  // state
  documents,
  selectedDocument,
  messages,
  loading,
  chatMode,
  modelSettings,
  savedConversations,
  activeTab,
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
  onChangeTab,
  // dark mode
  theme = 'light',
  onToggleTheme,
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

  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(false);

  const NavItem = ({ id, icon: Icon, label }) => {
    const btn = (
      <button
        className={cn(
          "w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm hover:bg-accent hover:text-accent-foreground",
          activeTab === id && "bg-accent text-accent-foreground",
          sidebarCollapsed && "justify-center"
        )}
        onClick={() => { onChangeTab(id); setMobileOpen(false); }}
        title={label}
      >
        <Icon className="h-5 w-5" />
        {!sidebarCollapsed && <span>{label}</span>}
      </button>
    );
    return sidebarCollapsed ? (
      <TooltipProvider delayDuration={100}>
        <Tooltip>
          <TooltipTrigger asChild>{btn}</TooltipTrigger>
          <TooltipContent side="right">{label}</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    ) : (
      btn
    );
  };

  return (
    <div className="h-full grid grid-rows-[auto_1fr]">
      {/* Top Nav */}
      <div className="border-b bg-card">
        <div className="px-4 py-3 flex items-center gap-2">
          <button className="md:hidden mr-auto" onClick={() => setMobileOpen(true)} aria-label="Open menu">
            <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
          </button>
          <div className="ml-auto flex items-center gap-2">
            <Button variant="outline" onClick={onToggleTheme} title="Toggle theme">
              {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
            <Button variant="outline" onClick={onToggleMode}>
              {chatMode === 'document' ? 'Use General' : 'Use Document'}
            </Button>
            <Button onClick={onNewChat} variant="secondary">
              <MessageSquare className="mr-2 h-4 w-4" /> New Chat
            </Button>
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="outline"><Settings className="mr-2 h-4 w-4" /> Model</Button>
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
      <div className={cn("grid grid-cols-1 overflow-hidden md:grid-cols-[300px_1fr]", sidebarCollapsed && "md:grid-cols-[72px_1fr]") }>
        {/* Sidebar (desktop) */}
        <div className="border-r bg-background hidden md:flex">
          <div className="h-full w-full flex flex-col">
            <div className="p-3 border-b">
              <div className="flex items-center justify-between">
                {sidebarCollapsed ? (
                  <div className="text-base font-semibold">DQ</div>
                ) : (
                  <div className="text-lg font-semibold">DocQueryAI</div>
                )}
                <Button variant="ghost" size="icon" onClick={()=>setSidebarCollapsed(!sidebarCollapsed)} title={sidebarCollapsed ? 'Expand' : 'Collapse'}>
                  {sidebarCollapsed ? <ChevronsRight className="h-4 w-4"/> : <ChevronsLeft className="h-4 w-4"/>}
                </Button>
              </div>
              <div className="space-y-2 mt-3">
                {!sidebarCollapsed && <div className="text-[11px] uppercase text-muted-foreground px-1">Navigation</div>}
                <NavItem id="chat" icon={MessageSquare} label="Chat" />
                <NavItem id="documents" icon={FileText} label="Documents" />
                <NavItem id="settings" icon={Settings} label="Settings" />
              </div>
            </div>
            {!sidebarCollapsed && (
              <div className="px-4 py-3 border-t space-y-2">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-muted-foreground">Conversations</div>
                  <div className="flex items-center gap-2">
                    <input ref={importRef} className="hidden" type="file" accept=".json" onChange={onImportConversations} />
                    <Button variant="outline" size="sm" onClick={() => importRef.current?.click()}>Import</Button>
                    <Button variant="outline" size="sm" onClick={onExportAllConversations} disabled={!savedConversations.length}><FiDownload className="mr-2" />Export</Button>
                  </div>
                </div>
                <ScrollArea className="h-48">
                  <div className="space-y-2">
                    {savedConversations.length === 0 ? (
                      <div className="text-xs text-muted-foreground px-2">No saved conversations.</div>
                    ) : (
                      savedConversations.map((conv) => (
                        <div key={conv.id} className="flex items-center justify-between gap-2 p-2 rounded-md border">
                          <button className="flex-1 text-left" onClick={() => { onLoadConversation(conv); onChangeTab('chat'); }}>
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
            )}
          </div>
        </div>
        {/* Sidebar (mobile) */}
        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetContent side="left">
            <SheetHeader>
              <SheetTitle>DocQueryAI</SheetTitle>
            </SheetHeader>
            <div className="mt-4 space-y-3">
              <div className="text-xs uppercase text-muted-foreground px-1">Navigation</div>
              <NavItem id="chat" icon={MessageSquare} label="Chat" />
              <NavItem id="documents" icon={FileText} label="Documents" />
              <NavItem id="settings" icon={Settings} label="Settings" />
              <div className="pt-4 border-t" />
              <div className="text-xs uppercase text-muted-foreground px-1">Conversations</div>
              <ScrollArea className="h-64">
                <div className="space-y-2">
                  {savedConversations.length === 0 ? (
                    <div className="text-xs text-muted-foreground px-2">No saved conversations.</div>
                  ) : (
                    savedConversations.map((conv) => (
                      <button key={conv.id} className="w-full text-left p-2 rounded-md border" onClick={() => { onLoadConversation(conv); onChangeTab('chat'); setMobileOpen(false); }}>
                        <div className="text-sm font-medium truncate">{conv.title}</div>
                        <div className="text-[11px] text-muted-foreground">{new Date(conv.timestamp).toLocaleString()}</div>
                      </button>
                    ))
                  )}
                </div>
              </ScrollArea>
            </div>
          </SheetContent>
        </Sheet>

        {/* Main content */}
        <div className="h-full">
          {activeTab === 'documents' && (
            <div className="h-full grid grid-rows-[auto_1fr]">
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
              <ScrollArea className="p-4">
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {documents.length === 0 ? (
                    <div className="text-sm text-muted-foreground">No documents uploaded.</div>
                  ) : (
                    documents.map((doc) => (
                      <Card key={doc.name}>
                        <CardContent className="p-3">
                          <div className="font-medium truncate">{doc.name}</div>
                          <div className="text-xs text-muted-foreground truncate">{doc.excerpt}</div>
                          <div className="mt-2">
                            <Button size="sm" variant="outline" onClick={()=>onSelectDocument(doc.name)}>Use in Chat</Button>
                          </div>
                        </CardContent>
                      </Card>
                    ))
                  )}
                </div>
              </ScrollArea>
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="p-4 max-w-3xl space-y-6">
              <div>
                <h1 className="text-xl font-semibold">Settings</h1>
                <p className="text-sm text-muted-foreground">Configure appearance and model behavior.</p>
              </div>
              <Card>
                <CardHeader>
                  <CardTitle>Appearance</CardTitle>
                  <CardDescription>Choose how DocQueryAI looks on your device.</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">Dark Mode</div>
                      <div className="text-sm text-muted-foreground">Switch between light and dark themes.</div>
                    </div>
                    <Switch checked={theme === 'dark'} onCheckedChange={onToggleTheme} />
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Model</CardTitle>
                  <CardDescription>Pick a model and tune generation settings.</CardDescription>
                </CardHeader>
                <CardContent>
                  <ModelSettings currentSettings={modelSettings} onSave={onUpdateModelSettings} />
                </CardContent>
              </Card>
            </div>
          )}

          {activeTab === 'chat' && (
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
          )}
        </div>
      </div>
    </div>
  );
}
