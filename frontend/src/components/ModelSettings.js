import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FiSettings, FiX } from 'react-icons/fi';

const API_URL = 'http://localhost:5001/api';

function ModelSettings({ onSave, currentSettings }) {
  const [isOpen, setIsOpen] = useState(false);
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [settings, setSettings] = useState({
    model: currentSettings?.model || 'deepseek-r1-distill-qwen-32b-mlx',
    temperature: currentSettings?.temperature || 0.7,
    maxTokens: currentSettings?.maxTokens || -1,
  });
  
  useEffect(() => {
    // Only fetch models when panel is opened
    if (isOpen) {
      fetchModels();
    }
  }, [isOpen]);
  
  const fetchModels = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.get(`${API_URL}/models`);
      if (response.data && response.data.data) {
        setModels(response.data.data);
      } else {
        setError('Invalid response format from API');
      }
    } catch (err) {
      console.error('Error fetching models:', err);
      setError('Failed to load available models');
    } finally {
      setLoading(false);
    }
  };
  
  const handleChange = (e) => {
    const { name, value } = e.target;
    setSettings({
      ...settings,
      [name]: name === 'temperature' || name === 'maxTokens' 
        ? parseFloat(value) 
        : value
    });
  };
  
  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(settings);
    setIsOpen(false);
  };
  
  return (
    <div className="model-settings">
      <button 
        className="settings-toggle"
        onClick={() => setIsOpen(!isOpen)}
        title={`Model: ${settings.model}`}
      >
        <FiSettings />
        {!isOpen && (
          <div className="current-model">
            {settings.model.split('-').slice(-1)[0]}
          </div>
        )}
      </button>
      
      {isOpen && (
        <div className="settings-panel">
          <div className="settings-header">
            <h3>Model Settings</h3>
            <button className="close-button" onClick={() => setIsOpen(false)}>
              <FiX />
            </button>
          </div>
          
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="model">Model</label>
              {loading ? (
                <div className="loading-models">Loading available models...</div>
              ) : error ? (
                <div className="error-message">{error}</div>
              ) : (
                <select 
                  id="model" 
                  name="model"
                  value={settings.model}
                  onChange={handleChange}
                  required
                >
                  {models.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.id}
                    </option>
                  ))}
                </select>
              )}
            </div>
            
            <div className="form-group">
              <label htmlFor="temperature">
                Temperature: {settings.temperature}
              </label>
              <input 
                type="range" 
                id="temperature" 
                name="temperature"
                min="0" 
                max="1.2" 
                step="0.1"
                value={settings.temperature}
                onChange={handleChange}
              />
              <div className="range-labels">
                <span>0 (Precise)</span>
                <span>1.2 (Creative)</span>
              </div>
            </div>
            
            <div className="form-group">
              <label htmlFor="maxTokens">Max Tokens</label>
              <select
                id="maxTokens"
                name="maxTokens"
                value={settings.maxTokens}
                onChange={handleChange}
              >
                <option value="-1">No limit</option>
                <option value="100">100</option>
                <option value="500">500</option>
                <option value="1000">1000</option>
                <option value="2000">2000</option>
                <option value="4000">4000</option>
                <option value="8000">8000</option>
              </select>
              <div className="setting-note">
                -1 means no limit (model decides when to stop)
              </div>
            </div>
            
            <button type="submit" className="save-settings">
              Apply Settings
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

export default ModelSettings;