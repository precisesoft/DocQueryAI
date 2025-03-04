import React, { useState, useRef } from 'react';
import { FiUpload, FiFile, FiMessageSquare, FiTrash2, FiDownload, FiUploadCloud } from 'react-icons/fi';

function Sidebar({ 
  documents, 
  selectedDocument, 
  onSelectDocument, 
  onUpload, 
  loading,
  savedConversations,
  onLoadConversation,
  onDeleteConversation,
  onExportConversation,
  onExportAllConversations,
  onImportConversations 
}) {
  const fileInputRef = useRef();
  const importInputRef = useRef();
  const [activeTab, setActiveTab] = useState('documents');

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      onUpload(file);
    }
  };
  
  const handleImportClick = () => {
    importInputRef.current.click();
  };

  return (
    <div className="sidebar">
      <div className="sidebar-tabs">
        <button 
          className={`tab ${activeTab === 'documents' ? 'active' : ''}`}
          onClick={() => setActiveTab('documents')}
        >
          Documents
        </button>
        <button 
          className={`tab ${activeTab === 'conversations' ? 'active' : ''}`}
          onClick={() => setActiveTab('conversations')}
        >
          Saved Chats
        </button>
      </div>
      
      {activeTab === 'documents' ? (
        <>
          <div className="upload-section">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".txt,.pdf"
              className="file-input"
              id="file-input"
              disabled={loading}
            />
            <label htmlFor="file-input" className="upload-button">
              <FiUpload /> Upload Document
            </label>
            {loading && <div className="loader"></div>}
          </div>
          
          <div className="document-list">
            {documents.length === 0 ? (
              <div className="no-documents">No documents uploaded yet</div>
            ) : (
              documents.map((doc, index) => (
                <div 
                  key={index}
                  className={`document-item ${selectedDocument === doc.name ? 'selected' : ''}`}
                  onClick={() => onSelectDocument(doc.name)}
                >
                  <FiFile className="document-icon" />
                  <div className="document-details">
                    <div className="document-name">{doc.name}</div>
                    <div className="document-excerpt">{doc.excerpt}...</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      ) : (
        <>
          <div className="conversation-actions">
            <button 
              className="action-button export-all"
              onClick={onExportAllConversations}
              disabled={savedConversations.length === 0}
              title="Export all conversations"
            >
              <FiDownload /> Export All
            </button>
            
            <input
              type="file"
              ref={importInputRef}
              onChange={onImportConversations}
              accept=".json"
              className="file-input"
              id="import-input"
            />
            <button 
              className="action-button import"
              onClick={handleImportClick}
              title="Import conversations from file"
            >
              <FiUploadCloud /> Import
            </button>
          </div>
          
          <div className="conversation-list">
            {savedConversations.length === 0 ? (
              <div className="no-conversations">No saved conversations yet</div>
            ) : (
              savedConversations.map((conv) => (
                <div key={conv.id} className="conversation-item">
                  <div 
                    className="conversation-title"
                    onClick={() => onLoadConversation(conv)}
                  >
                    <FiMessageSquare className="conversation-icon" />
                    <div>
                      <div className="conversation-name">{conv.title}</div>
                      <div className="conversation-date">
                        {new Date(conv.timestamp).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <div className="conversation-actions">
                    <button 
                      className="action-icon export"
                      onClick={(e) => {
                        e.stopPropagation();
                        onExportConversation(conv);
                      }}
                      title="Export conversation"
                    >
                      <FiDownload />
                    </button>
                    <button 
                      className="action-icon delete"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteConversation(conv.id);
                      }}
                      title="Delete conversation"
                    >
                      <FiTrash2 />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default Sidebar;