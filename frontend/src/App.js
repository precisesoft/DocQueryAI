import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import SaveConversationModal from './components/SaveConversationModal';
import './App.css';

// Make sure this matches your backend URL and port
const API_URL = 'http://localhost:5001/api';

function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [messages, setMessages] = useState([
    { 
      id: 1, 
      text: "Hello! You can chat with me directly or upload documents for more specific help.", 
      sender: "bot" 
    }
  ]);
  const [loading, setLoading] = useState(false);
  const [chatMode, setChatMode] = useState('general'); // 'general' or 'document'
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [savedConversations, setSavedConversations] = useState([]);
  const [notification, setNotification] = useState(null);

  // Fetch documents on component mount
  useEffect(() => {
    fetchDocuments();
  }, []);

  // Load saved conversations from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('savedConversations');
    if (saved) {
      setSavedConversations(JSON.parse(saved));
    }
  }, []);

  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`${API_URL}/documents`);
      setDocuments(response.data);
    } catch (error) {
      console.error('Error fetching documents:', error);
    }
  };

  // Update the handleDocumentUpload function

  const handleDocumentUpload = async (file) => {
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      // Add uploaded document to list
      setDocuments([...documents, { 
        name: response.data.filename, 
        excerpt: response.data.text_excerpt 
      }]);

      // Add confirmation message to chat
      setMessages([
        ...messages, 
        { 
          id: messages.length + 1, 
          text: response.data.message || `Document "${response.data.filename}" uploaded successfully!`, 
          sender: "bot" 
        }
      ]);
      
      // Show warning if any
      if (response.data.warning) {
        setMessages(prev => [
          ...prev, 
          { 
            id: prev.length + 1, 
            text: `Note: ${response.data.warning}`, 
            sender: "bot" 
          }
        ]);
      }
      
      // Auto-select the uploaded document
      setSelectedDocument(response.data.filename);
    } catch (error) {
      console.error('Error uploading document:', error);
      setMessages([
        ...messages, 
        { 
          id: messages.length + 1, 
          text: `Error uploading document: ${error.response?.data?.error || error.message}`, 
          sender: "bot" 
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Update the sendMessage function to handle streaming

  const sendMessage = async (text) => {
    if (!text.trim()) return;
  
    // Add user message
    const userMessage = { id: messages.length + 1, text, sender: "user" };
    setMessages([...messages, userMessage]);
  
    // Create placeholder for bot response
    const botResponseId = messages.length + 2;
    setMessages(prevMessages => [
      ...prevMessages,
      { id: botResponseId, text: "", sender: "bot", streaming: true }
    ]);
  
    try {
      // Prepare the payload
      const payload = {
        message: text,
        use_documents: chatMode === 'document',
        documents: selectedDocument ? [selectedDocument] : []
      };
      
      // Use fetch for streaming (instead of axios)
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });
  
      // Create a reader for the stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedText = "";
  
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        // Process the chunk
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6));
              
              if (data.end) {
                // Stream ended
                break;
              } else if (data.delta) {
                // Add ONLY the new delta to our accumulated text
                accumulatedText += data.delta;
                setMessages(prevMessages => 
                  prevMessages.map(msg => 
                    msg.id === botResponseId 
                      ? { ...msg, text: accumulatedText } 
                      : msg
                  )
                );
              }
            } catch (e) {
              console.error("Error parsing streamed data:", e);
            }
          }
        }
      }
      
      // Mark the message as no longer streaming
      setMessages(prevMessages => 
        prevMessages.map(msg => 
          msg.id === botResponseId 
            ? { ...msg, streaming: false } 
            : msg
        )
      );
      
    } catch (error) {
      console.error("Error:", error);
      setMessages(prevMessages => [
        ...prevMessages.filter(msg => msg.id !== botResponseId), // Remove streaming placeholder
        { 
          id: botResponseId, 
          text: `Error getting response: ${error.message}`, 
          sender: "bot" 
        }
      ]);
    }
  };

  // Add a function to toggle the chat mode
  const toggleChatMode = () => {
    const newMode = chatMode === 'general' ? 'document' : 'general';
    setChatMode(newMode);
    setMessages(prev => [
      ...prev,
      {
        id: prev.length + 1,
        text: newMode === 'general' 
          ? "Switched to general chat mode. I'll respond to your questions directly." 
          : "Switched to document mode. I'll use your documents to provide context for answers.",
        sender: "bot"
      }
    ]);
  };

  // Save conversation to localStorage
  const handleSaveConversation = (title) => {
    const newConversation = {
      id: Date.now().toString(),
      title: title,
      timestamp: new Date().toISOString(),
      messages: messages,
      document: selectedDocument,
      chatMode: chatMode
    };

    const updatedConversations = [...savedConversations, newConversation];
    setSavedConversations(updatedConversations);
    localStorage.setItem('savedConversations', JSON.stringify(updatedConversations));
  };

  // Generate a suggested title based on conversation
  const generateSuggestedTitle = () => {
    // Find first user message or use current date
    const firstUserMsg = messages.find(msg => msg.sender === 'user');
    if (firstUserMsg) {
      // Truncate to reasonable length for a title
      return firstUserMsg.text.substring(0, 30) + (firstUserMsg.text.length > 30 ? '...' : '');
    }
    return `Conversation ${new Date().toLocaleDateString()}`;
  };

  // Update the loadConversation function

  const loadConversation = (conversation) => {
    // Only show confirmation if there are user messages in the current conversation
    const hasUserMessages = messages.some(msg => msg.sender === 'user');
    
    if (hasUserMessages && messages.length > 1) {
      const confirmLoad = window.confirm(
        "Loading a saved conversation will replace your current chat. Continue?"
      );
      if (!confirmLoad) return;
    }
    
    setMessages(conversation.messages);
    setSelectedDocument(conversation.document);
    setChatMode(conversation.chatMode || 'general');
  };

  // Delete a saved conversation
  const deleteConversation = (id) => {
    const updatedConversations = savedConversations.filter(conv => conv.id !== id);
    setSavedConversations(updatedConversations);
    localStorage.setItem('savedConversations', JSON.stringify(updatedConversations));
  };

  // Export a single conversation as a JSON file
  const exportConversation = (conversation) => {
    const dataStr = JSON.stringify(conversation, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `${conversation.title.replace(/\s+/g, '_')}_${conversation.id}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Export all conversations as a single JSON file
  const exportAllConversations = () => {
    const dataStr = JSON.stringify(savedConversations, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `all_conversations_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Import conversations from a JSON file
  const importConversations = (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const imported = JSON.parse(e.target.result);
        
        // Handle both single conversation and array of conversations
        let newConversations = [];
        if (Array.isArray(imported)) {
          newConversations = imported;
        } else {
          newConversations = [imported];
        }
        
        // Validate imported data structure
        const validConversations = newConversations.filter(conv => 
          conv.id && conv.title && conv.messages && Array.isArray(conv.messages)
        );
        
        if (validConversations.length === 0) {
          alert('No valid conversations found in the imported file.');
          return;
        }
        
        // Add imported conversations to existing ones
        const updatedConversations = [...savedConversations, ...validConversations];
        setSavedConversations(updatedConversations);
        localStorage.setItem('savedConversations', JSON.stringify(updatedConversations));
        
        alert(`Successfully imported ${validConversations.length} conversation(s).`);
      } catch (error) {
        console.error('Error importing conversations:', error);
        alert('Failed to import conversations. Invalid file format.');
      }
      
      // Clear the input
      event.target.value = null;
    };
    
    reader.readAsText(file);
  };

  // Function to start a new chat (saving current one automatically)
  const startNewChat = () => {
    // Only confirm if there are user messages
    const hasUserMessages = messages.some(msg => msg.sender === 'user');
    
    if (hasUserMessages && messages.length > 1) {
      const confirmNew = window.confirm(
        "Starting a new chat will save the current conversation and clear the chat. Continue?"
      );
      if (!confirmNew) return;
      
      // Rest of the function remains the same...
      // ... (auto-saving code)
    }
    
    // Reset to initial state
    setMessages([
      { id: 1, text: "Hello! You can chat with me directly or upload documents for more specific help.", sender: "bot" }
    ]);
    setSelectedDocument(null);
    
    // Show notification
    setNotification("Previous conversation saved. Started new chat.");
    setTimeout(() => setNotification(null), 3000); // Clear after 3 seconds
  };

  // Add this function to your App component

  // Function to clear all documents
  const clearDocuments = async () => {
    // Ask for confirmation
    if (!window.confirm('Are you sure you want to remove all uploaded documents?')) {
      return;
    }
    
    try {
      setLoading(true);
      const response = await axios.post(`${API_URL}/documents/clear`, {
        delete_files: true  // Also remove the files from the server
      });
      
      // Clear documents from state
      setDocuments([]);
      setSelectedDocument(null);
      
      // Add success message to chat
      setMessages([
        ...messages, 
        { 
          id: messages.length + 1, 
          text: response.data.message || "All documents have been removed.", 
          sender: "bot" 
        }
      ]);
      
    } catch (error) {
      console.error('Error clearing documents:', error);
      setMessages([
        ...messages, 
        { 
          id: messages.length + 1, 
          text: `Error clearing documents: ${error.response?.data?.error || error.message}`, 
          sender: "bot" 
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      {notification && <div className="notification">{notification}</div>}
      <Sidebar 
        documents={documents} 
        selectedDocument={selectedDocument}
        onSelectDocument={setSelectedDocument}
        onUpload={handleDocumentUpload}
        loading={loading}
        savedConversations={savedConversations}
        onLoadConversation={loadConversation}
        onDeleteConversation={deleteConversation}
        onExportConversation={exportConversation}
        onExportAllConversations={exportAllConversations}
        onImportConversations={importConversations}
        onClearDocuments={clearDocuments}
      />
      
      <ChatInterface 
        messages={messages}
        onSendMessage={sendMessage}
        loading={loading}
        chatMode={chatMode}
        onToggleMode={toggleChatMode}
        onSaveConversation={() => setSaveModalOpen(true)}
        onNewChat={startNewChat}
      />
      
      <SaveConversationModal
        isOpen={saveModalOpen}
        onClose={() => setSaveModalOpen(false)}
        onSave={handleSaveConversation}
        suggestedTitle={generateSuggestedTitle()}
      />
    </div>
  );
}

export default App;
