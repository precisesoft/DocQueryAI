import React, { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { Button } from './ui/button';

function SaveConversationModal({ isOpen, onClose, onSave, suggestedTitle }) {
  const [title, setTitle] = useState(suggestedTitle || '');

  useEffect(() => {
    setTitle(suggestedTitle || '');
  }, [suggestedTitle, isOpen]);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave((title || suggestedTitle || 'Conversation').trim());
    setTitle('');
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open)=>{ if(!open) onClose(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Save Conversation</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 mt-2">
          <div className="space-y-2">
            <Label htmlFor="conversation-title">Conversation Title</Label>
            <Input
              id="conversation-title"
              value={title}
              onChange={(e)=>setTitle(e.target.value)}
              placeholder={suggestedTitle}
              autoFocus
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit">Save</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default SaveConversationModal;
