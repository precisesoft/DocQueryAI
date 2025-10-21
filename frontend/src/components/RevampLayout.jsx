import React, { useRef } from 'react';
import { Button } from './ui/button';
// Textarea is now replaced by Composer
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from './ui/card';
import { ScrollArea } from './ui/scroll-area';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from './ui/sheet';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible';
import { cn } from '../lib/utils';
import MessageBubble from './MessageBubble';
// Jobs dashboard removed per request
import ShipmentExtractor from './agents/ShipmentExtractor';
import Composer from './Composer';
import ModelSettings from './ModelSettings';
import { Moon, Sun, MessageSquare, FileText, Settings, ChevronsLeft, ChevronsRight, Upload, Trash2, Check, X, Search, MoreHorizontal, ChevronRight, User, SquarePen, Package } from 'lucide-react';
import ReactDOM from 'react-dom';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from './ui/tooltip';
import { Switch } from './ui/switch';
// import { Separator } from './ui/separator';
import { Input } from './ui/input';

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
  onRenameConversation,
  onChangeTab,
  onRunJob,
  // dark mode
  theme = 'light',
  onToggleTheme,
  // layout
  compact = false,
  onToggleCompact,
}) {
  const [input, setInput] = React.useState('');
  const fileRef = useRef();

  const handleSend = (e) => {
    e?.preventDefault();
    if (!loading && input.trim()) {
      onSendMessage(input);
      setInput('');
    }
  };

  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(false);
  const [editingId, setEditingId] = React.useState(null);
  const [editingValue, setEditingValue] = React.useState('');
  const [selectedConvId, setSelectedConvId] = React.useState(null);
  const [convQuery, setConvQuery] = React.useState('');
  const [menuOpenId, setMenuOpenId] = React.useState(null);
  const [menuPos, setMenuPos] = React.useState({ x: 0, y: 0 });

  // Keyboard shortcuts: N new chat, R rename selected, Delete delete selected
  React.useEffect(() => {
    const handler = (e) => {
      const tag = document.activeElement?.tagName?.toLowerCase();
      const isTyping = tag === 'input' || tag === 'textarea' || tag === 'select' || document.activeElement?.getAttribute('contenteditable') === 'true';
      if (isTyping) return;
      if (e.key === 'n' || e.key === 'N') {
        e.preventDefault();
        onNewChat();
        return;
      }
      if ((e.key === 'r' || e.key === 'R') && selectedConvId) {
        e.preventDefault();
        const conv = savedConversations.find(c => c.id === selectedConvId);
        if (conv) {
          setEditingId(conv.id);
          setEditingValue(conv.title);
        }
        return;
      }
      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedConvId) {
        e.preventDefault();
        onDeleteConversation(selectedConvId);
        return;
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [selectedConvId, savedConversations, onNewChat, onDeleteConversation]);

  // Close the three-dot menu on outside click
  React.useEffect(() => {
    const onDocClick = () => setMenuOpenId(null);
    window.addEventListener('click', onDocClick);
    return () => window.removeEventListener('click', onDocClick);
  }, []);

  const filteredConversations = React.useMemo(() => {
    const q = convQuery.trim().toLowerCase();
    if (!q) return savedConversations;
    return savedConversations.filter(c => (c.title || '').toLowerCase().includes(q));
  }, [convQuery, savedConversations]);

  const openMenu = (e, id, title) => {
    e.stopPropagation();
    const rect = e.currentTarget.getBoundingClientRect();
    const x = Math.max(8, rect.right - 160); // align menu to the right
    const y = rect.bottom + 6;
    setMenuPos({ x, y });
    setMenuOpenId(menuOpenId === id ? null : id);
  };

  const MenuPortal = ({ children }) => ReactDOM.createPortal(children, document.body);

  // Group conversations by date
  const groupConversationsByDate = (conversations) => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);
    const lastMonth = new Date(today);
    lastMonth.setMonth(lastMonth.getMonth() - 1);

    const groups = {
      today: [],
      yesterday: [],
      lastWeek: [],
      lastMonth: [],
      older: []
    };

    conversations.forEach(conv => {
      const convDate = new Date(conv.timestamp);
      if (convDate >= today) {
        groups.today.push(conv);
      } else if (convDate >= yesterday) {
        groups.yesterday.push(conv);
      } else if (convDate >= lastWeek) {
        groups.lastWeek.push(conv);
      } else if (convDate >= lastMonth) {
        groups.lastMonth.push(conv);
      } else {
        groups.older.push(conv);
      }
    });

    return groups;
  };

  const groupedConversations = React.useMemo(() => {
    return groupConversationsByDate(filteredConversations);
  }, [filteredConversations]);

  const [openGroups, setOpenGroups] = React.useState({
    today: true,
    yesterday: true,
    lastWeek: false,
    lastMonth: false,
    older: false
  });

  const toggleGroup = (group) => {
    setOpenGroups(prev => ({ ...prev, [group]: !prev[group] }));
  };

  const ConversationItem = ({ conv, isMobile = false }) => (
    <div
      key={conv.id}
      className={cn(
        "group w-full overflow-hidden flex items-center justify-between gap-2 px-2 py-1 rounded-lg transition-all",
        "hover:bg-accent/60",
        selectedConvId === conv.id && "bg-accent/80"
      )}
      onMouseEnter={() => setSelectedConvId(conv.id)}
    >
      {editingId === conv.id ? (
        <div className="flex-1 min-w-0 flex items-center gap-2">
          <Input
            value={editingValue}
            onChange={(e) => setEditingValue(e.target.value)}
            className="h-8"
            autoFocus
            onFocus={(e) => e.target.select()}
          />
          <Button
            size="icon"
            variant="secondary"
            onClick={() => {
              const v = editingValue.trim();
              if (v) onRenameConversation(conv.id, v);
              setEditingId(null);
            }}
            title="Save"
          >
            <Check className="h-4 w-4" />
          </Button>
          <Button size="icon" variant="ghost" onClick={() => setEditingId(null)} title="Cancel">
            <X className="h-4 w-4" />
          </Button>
        </div>
      ) : (
        <>
          <button
            className="flex-1 min-w-0 text-left relative z-10"
            onClick={() => {
              onLoadConversation(conv);
              onChangeTab('chat');
              setSelectedConvId(conv.id);
              if (isMobile) setMobileOpen(false);
            }}
          >
            <div className="text-sm font-medium truncate">{conv.title || 'Untitled chat'}</div>
          </button>
          <div className="relative shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              aria-label="More options"
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={(e) => openMenu(e, conv.id, conv.title)}
            >
              <MoreHorizontal className="h-4 w-4" />
            </Button>
            {menuOpenId === conv.id && (
              <MenuPortal>
                <div
                  className="fixed z-[60] w-40 rounded-md border bg-popover shadow-md"
                  style={{ left: menuPos.x, top: menuPos.y }}
                >
                  <button
                    className="w-full text-left px-3 py-2 text-sm hover:bg-accent rounded-t-md"
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingId(conv.id);
                      setEditingValue(conv.title || '');
                      setMenuOpenId(null);
                    }}
                  >
                    Rename
                  </button>
                  <button
                    className="w-full text-left px-3 py-2 text-sm text-destructive hover:bg-accent rounded-b-md"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteConversation(conv.id);
                      setMenuOpenId(null);
                    }}
                  >
                    Delete
                  </button>
                </div>
              </MenuPortal>
            )}
          </div>
        </>
      )}
    </div>
  );

  const ConversationGroup = ({ title, conversations, groupKey }) => {
    if (conversations.length === 0) return null;

    return (
      <Collapsible open={openGroups[groupKey]} onOpenChange={() => toggleGroup(groupKey)}>
        <CollapsibleTrigger className="w-full flex items-center gap-2 px-2 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors">
          <ChevronRight className={cn("h-3 w-3 transition-transform", openGroups[groupKey] && "rotate-90")} />
          {title}
        </CollapsibleTrigger>
        <CollapsibleContent className="space-y-1 mt-1">
          {conversations.map(conv => (
            <ConversationItem key={conv.id} conv={conv} />
          ))}
        </CollapsibleContent>
      </Collapsible>
    );
  };

  return (
    <div className={cn("h-full grid grid-cols-1 md:grid-cols-[260px_minmax(0,1fr)]", sidebarCollapsed && "md:grid-cols-[72px_minmax(0,1fr)]") }>
      {/* Sidebar (desktop) full height - ChatGPT Style */}
      <div className="hidden md:flex h-full border-r bg-background relative z-10 shrink-0 min-w-0">
        {!sidebarCollapsed ? (
          <div className="h-full w-full flex flex-col">
            {/* Top Section */}
            <div className="p-3 space-y-2">
              <div className="flex items-center justify-between mb-2">
                <div className="text-lg font-semibold">DocQueryAI</div>
                <Button variant="ghost" size="icon" onClick={() => setSidebarCollapsed(true)} title="Collapse">
                  <ChevronsLeft className="h-4 w-4" />
                </Button>
              </div>

              {/* New Chat Button */}
              <Button onClick={onNewChat} className="w-full justify-start" variant="outline">
                <SquarePen className="mr-2 h-4 w-4" />
                New chat
              </Button>

              {/* Search */}
              <div className="relative">
                <Input
                  value={convQuery}
                  onChange={(e) => setConvQuery(e.target.value)}
                  placeholder="Search chats"
                  className="pl-8 h-9"
                />
                <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              </div>
            </div>

            {/* Navigation Items */}
            <div className="px-3 space-y-1">
              <Button
                variant="ghost"
                className="w-full justify-start"
                onClick={() => onChangeTab('documents')}
              >
                <FileText className="mr-2 h-4 w-4" />
                Documents
              </Button>
              <Button
                variant="ghost"
                className="w-full justify-start"
                onClick={() => onChangeTab('extractor')}
              >
                <Package className="mr-2 h-4 w-4" />
                Shipment Data Extractor
              </Button>
              {/* Jobs entry removed per request */}
              <Button
                variant="ghost"
                className="w-full justify-start"
                onClick={() => onChangeTab('settings')}
              >
                <Settings className="mr-2 h-4 w-4" />
                Settings
              </Button>
            </div>

            <div className="h-px bg-border my-2" />

            {/* Conversations */}
            <ScrollArea className="flex-1 min-h-0 px-3">
              <div className="space-y-1 pb-3">
                {filteredConversations.length === 0 ? (
                  <div className="text-center py-8 px-4">
                    <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground/30 mb-3" />
                    <p className="text-sm text-muted-foreground">No chats yet</p>
                    <p className="text-xs text-muted-foreground/70 mt-1">Start a new chat to begin</p>
                  </div>
                ) : (
                  <>
                    <ConversationGroup title="Today" conversations={groupedConversations.today} groupKey="today" />
                    <ConversationGroup title="Yesterday" conversations={groupedConversations.yesterday} groupKey="yesterday" />
                    <ConversationGroup title="Previous 7 Days" conversations={groupedConversations.lastWeek} groupKey="lastWeek" />
                    <ConversationGroup title="Previous 30 Days" conversations={groupedConversations.lastMonth} groupKey="lastMonth" />
                    <ConversationGroup title="Older" conversations={groupedConversations.older} groupKey="older" />
                  </>
                )}
              </div>
            </ScrollArea>

            {/* User Profile at Bottom */}
            <div className="border-t p-3">
              <Button variant="ghost" className="w-full justify-start">
                <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center mr-2">
                  <User className="h-4 w-4" />
                </div>
                <span className="text-sm font-medium truncate">User</span>
              </Button>
            </div>
          </div>
        ) : (
          // Collapsed Sidebar
          <div className="h-full w-full flex flex-col items-center py-3 space-y-2">
            <Button variant="ghost" size="icon" onClick={() => setSidebarCollapsed(false)} title="Expand">
              <ChevronsRight className="h-4 w-4" />
            </Button>
            <TooltipProvider delayDuration={100}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" onClick={onNewChat}>
                    <SquarePen className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">New chat</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <div className="h-px w-6 bg-border my-2" />
            <TooltipProvider delayDuration={100}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" onClick={() => onChangeTab('documents')}>
                    <FileText className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">Documents</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider delayDuration={100}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" onClick={() => onChangeTab('settings')}>
                    <Settings className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">Settings</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <div className="flex-1" />
            <TooltipProvider delayDuration={100}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon">
                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                      <User className="h-4 w-4" />
                    </div>
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">User Profile</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        )}
      </div>

      {/* Main area with header */}
      <div className="h-full min-h-0 flex flex-col min-w-0 relative z-0 overflow-x-hidden">
        <div className="border-b bg-card px-4 py-3 flex items-center gap-2">
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
          </div>
        </div>
        <div className="flex-1 min-h-0">
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
                        <Upload className="mr-2 h-4 w-4" /> {loading ? 'Uploading...' : 'Choose File'}
                      </Button>
                      <Button variant="outline" onClick={onClearDocuments} disabled={!documents.length}>
                        <Trash2 className="mr-2 h-4 w-4" /> Clear All
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
                          <div className="mt-2 flex gap-2">
                            <Button size="sm" variant="outline" onClick={()=>onSelectDocument(doc.name)}>Use in Chat</Button>
                            <Button size="sm" onClick={()=>onRunJob?.(doc.name)}>Extract Entry Detail</Button>
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
                  <div className="mt-4 flex items-center justify-between">
                    <div>
                      <div className="font-medium">Compact Mode</div>
                      <div className="text-sm text-muted-foreground">Tighter spacing and narrower bubbles.</div>
                    </div>
                    <Switch checked={compact} onCheckedChange={onToggleCompact} />
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

          

          {activeTab === 'extractor' && (
            <div className="h-full">
              <ShipmentExtractor />
            </div>
          )}

          {activeTab === 'chat' && (
            <div className="h-full grid grid-rows-[1fr_auto] min-h-0">
              <ScrollArea className="h-full min-h-0 px-0 py-2">
                <div className={cn("w-full max-w-3xl mx-auto px-3", compact ? "space-y-1.5" : "space-y-2") }>
                  {messages.map((m) => (
                    <MessageBubble key={m.id} message={m.text} sender={m.sender} streaming={m.streaming} compact={compact} />
                  ))}
                </div>
              </ScrollArea>
              <Composer
                value={input}
                onChange={setInput}
                onSubmit={handleSend}
                onUpload={(file)=>onUpload(file)}
                loading={loading}
                compact={compact}
                placeholder=""
              />
            </div>
          )}
        </div>
      </div>

      {/* Sidebar (mobile) - ChatGPT Style */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-[280px] p-0">
          <div className="h-full flex flex-col">
            {/* Top Section */}
            <div className="p-4 space-y-3 border-b">
              <SheetHeader>
                <SheetTitle>DocQueryAI</SheetTitle>
              </SheetHeader>

              {/* New Chat Button */}
              <Button onClick={() => { onNewChat(); setMobileOpen(false); }} className="w-full justify-start" variant="outline">
                <SquarePen className="mr-2 h-4 w-4" />
                New chat
              </Button>

              {/* Search */}
              <div className="relative">
                <Input
                  value={convQuery}
                  onChange={(e) => setConvQuery(e.target.value)}
                  placeholder="Search chats"
                  className="pl-8 h-9"
                />
                <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              </div>
            </div>

            {/* Navigation Items */}
            <div className="px-4 py-3 space-y-1 border-b">
              <Button
                variant="ghost"
                className="w-full justify-start"
                onClick={() => { onChangeTab('documents'); setMobileOpen(false); }}
              >
                <FileText className="mr-2 h-4 w-4" />
                Documents
              </Button>
              <Button
                variant="ghost"
                className="w-full justify-start"
                onClick={() => { onChangeTab('extractor'); setMobileOpen(false); }}
              >
                <Package className="mr-2 h-4 w-4" />
                Shipment Data Extractor
              </Button>
              {/* Jobs page removed per request */}
              <Button
                variant="ghost"
                className="w-full justify-start"
                onClick={() => { onChangeTab('settings'); setMobileOpen(false); }}
              >
                <Settings className="mr-2 h-4 w-4" />
                Settings
              </Button>
            </div>

            {/* Conversations */}
            <ScrollArea className="flex-1 px-4">
              <div className="space-y-1 py-3">
                {filteredConversations.length === 0 ? (
                  <div className="text-center py-8 px-4">
                    <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground/30 mb-3" />
                    <p className="text-sm text-muted-foreground">No chats yet</p>
                    <p className="text-xs text-muted-foreground/70 mt-1">Start a new chat to begin</p>
                  </div>
                ) : (
                  <>
                    {groupedConversations.today.length > 0 && (
                      <Collapsible open={openGroups.today} onOpenChange={() => toggleGroup('today')}>
                        <CollapsibleTrigger className="w-full flex items-center gap-2 px-2 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground">
                          <ChevronRight className={cn("h-3 w-3 transition-transform", openGroups.today && "rotate-90")} />
                          Today
                        </CollapsibleTrigger>
                        <CollapsibleContent className="space-y-1 mt-1">
                          {groupedConversations.today.map(conv => (
                            <ConversationItem key={conv.id} conv={conv} isMobile={true} />
                          ))}
                        </CollapsibleContent>
                      </Collapsible>
                    )}
                    {groupedConversations.yesterday.length > 0 && (
                      <Collapsible open={openGroups.yesterday} onOpenChange={() => toggleGroup('yesterday')}>
                        <CollapsibleTrigger className="w-full flex items-center gap-2 px-2 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground">
                          <ChevronRight className={cn("h-3 w-3 transition-transform", openGroups.yesterday && "rotate-90")} />
                          Yesterday
                        </CollapsibleTrigger>
                        <CollapsibleContent className="space-y-1 mt-1">
                          {groupedConversations.yesterday.map(conv => (
                            <ConversationItem key={conv.id} conv={conv} isMobile={true} />
                          ))}
                        </CollapsibleContent>
                      </Collapsible>
                    )}
                    {groupedConversations.lastWeek.length > 0 && (
                      <Collapsible open={openGroups.lastWeek} onOpenChange={() => toggleGroup('lastWeek')}>
                        <CollapsibleTrigger className="w-full flex items-center gap-2 px-2 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground">
                          <ChevronRight className={cn("h-3 w-3 transition-transform", openGroups.lastWeek && "rotate-90")} />
                          Previous 7 Days
                        </CollapsibleTrigger>
                        <CollapsibleContent className="space-y-1 mt-1">
                          {groupedConversations.lastWeek.map(conv => (
                            <ConversationItem key={conv.id} conv={conv} isMobile={true} />
                          ))}
                        </CollapsibleContent>
                      </Collapsible>
                    )}
                    {groupedConversations.lastMonth.length > 0 && (
                      <Collapsible open={openGroups.lastMonth} onOpenChange={() => toggleGroup('lastMonth')}>
                        <CollapsibleTrigger className="w-full flex items-center gap-2 px-2 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground">
                          <ChevronRight className={cn("h-3 w-3 transition-transform", openGroups.lastMonth && "rotate-90")} />
                          Previous 30 Days
                        </CollapsibleTrigger>
                        <CollapsibleContent className="space-y-1 mt-1">
                          {groupedConversations.lastMonth.map(conv => (
                            <ConversationItem key={conv.id} conv={conv} isMobile={true} />
                          ))}
                        </CollapsibleContent>
                      </Collapsible>
                    )}
                    {groupedConversations.older.length > 0 && (
                      <Collapsible open={openGroups.older} onOpenChange={() => toggleGroup('older')}>
                        <CollapsibleTrigger className="w-full flex items-center gap-2 px-2 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground">
                          <ChevronRight className={cn("h-3 w-3 transition-transform", openGroups.older && "rotate-90")} />
                          Older
                        </CollapsibleTrigger>
                        <CollapsibleContent className="space-y-1 mt-1">
                          {groupedConversations.older.map(conv => (
                            <ConversationItem key={conv.id} conv={conv} isMobile={true} />
                          ))}
                        </CollapsibleContent>
                      </Collapsible>
                    )}
                  </>
                )}
              </div>
            </ScrollArea>

            {/* User Profile at Bottom */}
            <div className="border-t p-4">
              <Button variant="ghost" className="w-full justify-start">
                <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center mr-2">
                  <User className="h-4 w-4" />
                </div>
                <span className="text-sm font-medium truncate">User</span>
              </Button>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
