import React, { useState } from 'react';

function SaveConversationModal({ isOpen, onClose, onSave, suggestedTitle }) {
  const [title, setTitle] = useState(suggestedTitle || '');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(title.trim() || suggestedTitle);
    setTitle('');
    onClose();
  };

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h2>Save Conversation</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="conversation-title">Conversation Title</label>
            <input
              type="text"
              id="conversation-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={suggestedTitle}
              autoFocus
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn-cancel" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-save">Save</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default SaveConversationModal;