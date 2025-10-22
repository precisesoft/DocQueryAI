import React from 'react';
import { Button } from '../ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/card';
import { ScrollArea } from '../ui/scroll-area';
// import { Input } from '../ui/input';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001/api';

function Summary({ meta, elapsed }) {
  if (!meta) return null;
  const schemaOk = meta.validation?.schema_ok;
  const oc = meta.overall_confidence != null ? `${(meta.overall_confidence*100).toFixed(1)}%` : '-';
  const warnings = meta.validation?.warnings || [];
  const missing = meta.missing_evidence_paths || [];
  return (
    <div className="space-y-2 text-sm">
      <div><span className="font-medium">Schema:</span> {schemaOk ? 'OK' : 'FAIL'}</div>
      <div><span className="font-medium">Overall Confidence:</span> {oc}</div>
      <div><span className="font-medium">Elapsed:</span> {elapsed ? `${elapsed.toFixed(1)}s` : '-'}</div>
      {warnings.length > 0 && (
        <div>
          <div className="font-medium">Warnings:</div>
          <ul className="list-disc ml-5 text-muted-foreground">
            {warnings.slice(0,5).map((w,i)=>(<li key={i}>{w}</li>))}
          </ul>
        </div>
      )}
      {missing.length > 0 && (
        <div>
          <div className="font-medium">Missing Evidence Paths ({missing.length}):</div>
          <ScrollArea className="h-24 mt-1">
            <ul className="list-disc ml-5 text-muted-foreground">
              {missing.slice(0,20).map((p,i)=>(<li key={i}>{p}</li>))}
            </ul>
          </ScrollArea>
        </div>
      )}
    </div>
  );
}

function Modal({ title, open, onClose, children }){
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={onClose}>
      <div className="max-w-5xl w-full bg-background rounded shadow" onClick={(e)=>e.stopPropagation()}>
        <div className="border-b px-4 py-2 flex items-center justify-between">
          <div className="font-medium">{title}</div>
          <Button variant="ghost" size="sm" onClick={onClose}>Close</Button>
        </div>
        <div className="p-4 h-[70vh] overflow-hidden">{children}</div>
      </div>
    </div>
  );
}

export default function ShipmentExtractor() {
  const [selected, setSelected] = React.useState('');
  const [job, setJob] = React.useState(null); // { job_id, status, events }
  const [result, setResult] = React.useState(null); // wrapper json
  const [elapsed, setElapsed] = React.useState(null);
  const [busy, setBusy] = React.useState(false);
  const [jobs, setJobs] = React.useState([]);
  const [viewJob, setViewJob] = React.useState(null);
  const [viewLogsJob, setViewLogsJob] = React.useState(null);
  const [uploading, setUploading] = React.useState(false);
  const [uploadMsg, setUploadMsg] = React.useState('');
  const fileRef = React.useRef();

  // pick up a recent job if one was queued (e.g., from Documents page action)
  React.useEffect(()=>{
    const jid = localStorage.getItem('latestJobId');
    if (jid) {
      setJob({ job_id: jid, status: 'queued' });
    }
  }, []);

  const onUpload = async (file) => {
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    setUploading(true);
    setUploadMsg('Uploading…');
    try {
      const r = await fetch(`${API_URL}/upload`, { method:'POST', body: form });
      const j = await r.json();
      if (!r.ok) throw new Error(j?.error || r.status);
      setSelected(j.filename);
      setUploadMsg(`Uploaded: ${j.filename}`);
    } catch(e) {
      setUploadMsg(`Upload failed: ${e.message}`);
    } finally {
      setUploading(false);
    }
  };

  const startJob = async (filename) => {
    setBusy(true);
    setJob(null); setResult(null); setElapsed(null);
    try {
      const r = await fetch(`${API_URL}/jobs/create`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ filename, max_pages:2, scale:1.6, model:'gemma3:12b', agent_version:'v1' })
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j?.error || r.status);
      setJob({ job_id: j.job_id, status: j.status || 'queued' });
      localStorage.setItem('latestJobId', j.job_id);
    } catch(e) {
      alert(`Failed to queue job: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  // Poll job status
  React.useEffect(()=>{
    let alive = true;
    const t = setInterval(async ()=>{
      try {
        const r = await fetch(`${API_URL}/jobs`);
        if (!alive) return;
        const j = await r.json();
        setJobs(j.jobs || []);
      } catch(e) { /* ignore */ }
    }, 3000);
    return ()=>{ alive=false; clearInterval(t); };
  }, []);

  const openOutput = async (job_id) => {
    setViewJob({ job_id, loading: true, result: null });
    try {
      const rr = await fetch(`${API_URL}/jobs/${job_id}/result`);
      const wrapper = await rr.json();
      setViewJob({ job_id, loading: false, result: wrapper });
    } catch (e) {
      setViewJob({ job_id, loading: false, error: e.message });
    }
  };

  const openLogs = async (job_id) => {
    setViewLogsJob({ job_id, loading: true, data: null });
    try {
      const r = await fetch(`${API_URL}/jobs/${job_id}`);
      const j = await r.json();
      setViewLogsJob({ job_id, loading: false, data: j });
    } catch (e) {
      setViewLogsJob({ job_id, loading: false, error: e.message });
    }
  };

  const deleteJob = async (job_id) => {
    if (!window.confirm('Delete this job and its artifacts?')) return;
    try {
      const r = await fetch(`${API_URL}/jobs/${job_id}`, { method: 'DELETE' });
      if (!r.ok) {
        const t = await r.text();
        alert(`Delete failed: ${t}`);
        return;
      }
      // refresh jobs
      const jr = await fetch(`${API_URL}/jobs`);
      const jj = await jr.json();
      setJobs(jj.jobs || []);
    } catch (e) {
      alert(`Delete failed: ${e.message}`);
    }
  };

  return (
    <div className="h-full grid grid-rows-[auto_1fr]">
      <div className="p-4 border-b">
        <Card>
          <CardHeader>
            <CardTitle>Shipment Data Extractor</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-center gap-2">
              <input ref={fileRef} type="file" className="hidden" accept=".pdf" onChange={(e)=>onUpload(e.target.files[0])} />
              <Button onClick={()=>fileRef.current?.click()} disabled={busy || uploading}>{uploading ? 'Uploading…' : 'Upload PDF'}</Button>
              <Button onClick={()=> selected && startJob(selected)} disabled={!selected || busy || uploading}>Extract</Button>
            </div>
            <div className="mt-2 text-xs text-muted-foreground">
              {uploadMsg || (selected ? `Ready: ${selected}` : 'No file selected yet.')}
            </div>
            {job?.job_id && (
              <div className="mt-3 text-sm">
                <div><span className="font-medium">Job:</span> {job.job_id}</div>
                <div><span className="font-medium">Status:</span> {job.status}</div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      <div className="p-4">
        <Card>
          <CardHeader>
            <CardTitle>Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="w-full overflow-auto">
              <table className="w-full text-sm">
                <thead className="text-xs text-muted-foreground border-b">
                  <tr>
                    <th className="text-left py-2 pr-3">File</th>
                    <th className="text-left py-2 pr-3">Size</th>
                    <th className="text-left py-2 pr-3">Uploaded</th>
                    <th className="text-left py-2 pr-3">Job</th>
                    <th className="text-left py-2 pr-3">Status</th>
                    <th className="text-left py-2 pr-3">Elapsed</th>
                    <th className="text-left py-2 pr-3">Confidence</th>
                    <th className="text-left py-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.length === 0 ? (
                    <tr><td colSpan={8} className="py-4 text-muted-foreground">No jobs yet. Upload a PDF above to start.</td></tr>
                  ) : jobs.map(j => {
                    const sizeKB = j.size_bytes ? `${(j.size_bytes/1024).toFixed(1)} KB` : '-';
                    const ts = j.created_at ? new Date(j.created_at).toLocaleString() : '-';
                    const shortId = (j.job_id||'').slice(0,8);
                    const oc = j.overall_confidence != null ? `${(j.overall_confidence*100).toFixed(1)}%` : '-';
                    return (
                      <tr key={j.job_id} className="border-b last:border-0">
                        <td className="py-2 pr-3 truncate max-w-[220px]" title={j.filename}>{j.filename}</td>
                        <td className="py-2 pr-3">{sizeKB}</td>
                        <td className="py-2 pr-3">{ts}</td>
                        <td className="py-2 pr-3"><span className="font-mono text-xs">{shortId}</span></td>
                        <td className="py-2 pr-3">
                          <span className="px-2 py-0.5 rounded bg-secondary text-secondary-foreground uppercase text-[10px]">{j.status}</span>
                        </td>
                        <td className="py-2 pr-3">{j.elapsed_sec ? `${j.elapsed_sec.toFixed(1)}s` : '-'}</td>
                        <td className="py-2 pr-3">{oc}</td>
                        <td className="py-2">
                          <div className="flex gap-2">
                            <Button size="sm" variant="outline" onClick={()=>openOutput(j.job_id)} disabled={j.status!=='done'}>View Output</Button>
                            <Button size="sm" variant="outline" onClick={()=>openLogs(j.job_id)}>View Logs</Button>
                            {j.status==='done' && (
                              <a href={`${API_URL}/jobs/${j.job_id}/result`} target="_blank" rel="noreferrer"><Button size="sm">Download</Button></a>
                            )}
                            {(j.status==='queued' || j.status==='running' || j.status==='cancel_requested') && (
                              <Button size="sm" variant="outline" onClick={async ()=>{
                                try {
                                  const r = await fetch(`${API_URL}/jobs/${j.job_id}/cancel`, { method:'POST' });
                                  if (!r.ok) throw new Error(await r.text());
                                  const jr = await fetch(`${API_URL}/jobs`);
                                  const jj = await jr.json();
                                  setJobs(jj.jobs || []);
                                } catch(e) { alert(`Cancel failed: ${e.message}`); }
                              }}>Cancel</Button>
                            )}
                            <Button size="sm" variant="destructive" onClick={()=>deleteJob(j.job_id)} disabled={j.status==='running'}>Delete</Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      <Modal title={`Job Output: ${viewJob?.job_id||''}`} open={!!viewJob} onClose={()=>setViewJob(null)}>
        {!viewJob?.result ? (
          <div className="text-sm text-muted-foreground">{viewJob?.loading ? 'Loading output…' : viewJob?.error || 'No data'}</div>
        ) : (
          <div className="flex flex-col h-full">
            <div className="shrink-0"><Summary meta={viewJob.result.meta} elapsed={viewJob.result.meta?.elapsed_sec} /></div>
            <div className="h-3" />
            <div className="grow min-h-0">
              <ScrollArea className="h-full">
                <pre className="text-xs whitespace-pre-wrap break-words bg-muted/30 p-3 rounded">{JSON.stringify(viewJob.result.data, null, 2)}</pre>
              </ScrollArea>
            </div>
          </div>
        )}
      </Modal>

      <Modal title={`Job Logs: ${viewLogsJob?.job_id||''}`} open={!!viewLogsJob} onClose={()=>setViewLogsJob(null)}>
        {!viewLogsJob?.data ? (
          <div className="text-sm text-muted-foreground">{viewLogsJob?.loading ? 'Loading logs…' : viewLogsJob?.error || 'No logs'}</div>
        ) : (
          <div className="h-full">
            <ScrollArea className="h-full">
              <ul className="text-xs space-y-1">
                {(viewLogsJob.data.events||[]).map((e,i)=>(<li key={i}><span className="text-muted-foreground">{e.ts}</span> — {e.message}</li>))}
              </ul>
            </ScrollArea>
          </div>
        )}
      </Modal>
    </div>
  );
}
