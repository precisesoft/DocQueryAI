import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
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

  // Fetch documents on component mount
  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`${API_URL}/documents`);
      setDocuments(response.data);
    } catch (error) {
      console.error('Error fetching documents:', error);
    }
  };

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
          text: `Document "${response.data.filename}" uploaded successfully!`, 
          sender: "bot" 
        }
      ]);
      
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
              } else if (data.text) {
                // Update the message with the new text
                accumulatedText += data.text;
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

  return (
    <div className="app-container">
      <Sidebar 
        documents={documents} 
        selectedDocument={selectedDocument}
        onSelectDocument={setSelectedDocument}
        onUpload={handleDocumentUpload}
        loading={loading}
      />
      <ChatInterface 
        messages={messages}
        onSendMessage={sendMessage}
        loading={loading}
        chatMode={chatMode}
        onToggleMode={toggleChatMode}
      />
    </div>
  );
}

export default App;
