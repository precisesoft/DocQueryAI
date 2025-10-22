import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Label } from './ui/label';
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from './ui/select';
import { Button } from './ui/button';
import { Slider } from './ui/slider';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001/api';

function ModelSettings({ onSave, currentSettings }) {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [settings, setSettings] = useState({
    model: currentSettings?.model || 'phi3:mini',
    temperature: currentSettings?.temperature || 0.7,
    maxTokens: currentSettings?.maxTokens || -1,
  });

  useEffect(() => {
    fetchModels();
    // sync if parent changes
    setSettings({
      model: currentSettings?.model || 'phi3:mini',
      temperature: currentSettings?.temperature || 0.7,
      maxTokens: currentSettings?.maxTokens || -1,
    });
  }, [currentSettings]);

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

  return (
    <form
      onSubmit={(e)=>{ e.preventDefault(); onSave(settings); }}
      className="space-y-4"
    >
      <div className="space-y-2">
        <Label>Model</Label>
        {loading ? (
          <div className="text-sm text-muted-foreground">Loading available models…</div>
        ) : error ? (
          <div className="text-sm text-destructive">{error}</div>
        ) : (
          <Select value={settings.model} onValueChange={(v)=>setSettings({...settings, model: v})}>
            <SelectTrigger>
              <SelectValue placeholder="Select a model" />
            </SelectTrigger>
            <SelectContent>
              {models.map((m)=> (
                <SelectItem key={m.id} value={m.id}>{m.id}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="temperature">Temperature</Label>
          <div className="text-xs text-muted-foreground">{settings.temperature.toFixed(1)}</div>
        </div>
        <Slider
          min={0}
          max={1.2}
          step={0.1}
          value={[settings.temperature]}
          onValueChange={(v)=>setSettings({...settings, temperature: Number(v[0])})}
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>0 (Precise)</span>
          <span>1.2 (Creative)</span>
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="maxTokens">Max Tokens</Label>
        <Select value={String(settings.maxTokens)} onValueChange={(v)=>setSettings({...settings, maxTokens: parseFloat(v)})}>
          <SelectTrigger>
            <SelectValue placeholder="Max tokens" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={"-1"}>No limit</SelectItem>
            <SelectItem value={"100"}>100</SelectItem>
            <SelectItem value={"500"}>500</SelectItem>
            <SelectItem value={"1000"}>1000</SelectItem>
            <SelectItem value={"2000"}>2000</SelectItem>
            <SelectItem value={"4000"}>4000</SelectItem>
            <SelectItem value={"8000"}>8000</SelectItem>
          </SelectContent>
        </Select>
        <div className="text-xs text-muted-foreground">-1 means no limit (model decides when to stop)</div>
      </div>
      <div className="flex justify-end">
        <Button type="submit">Apply Settings</Button>
      </div>
    </form>
  );
}

export default ModelSettings;
