import React, { useRef } from 'react';
import { FiUpload, FiFile } from 'react-icons/fi';

function Sidebar({ documents, selectedDocument, onSelectDocument, onUpload, loading }) {
  const fileInputRef = useRef();

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      onUpload(file);
    }
  };

  return (
    <div className="sidebar">
      <h2>Documents</h2>
      
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
    </div>
  );
}

export default Sidebar;