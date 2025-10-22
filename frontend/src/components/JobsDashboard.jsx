import React from 'react';
import { Button } from './ui/button';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { ScrollArea } from './ui/scroll-area';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001/api';

function JobRow({ job, onView }) {
  const { job_id, filename, status, created_at, updated_at, elapsed_sec, schema_ok, overall_confidence } = job;
  const shortId = job_id?.slice(0, 8);
  const oc = overall_confidence != null ? `${(overall_confidence*100).toFixed(1)}%` : '-';
  return (
    <div className="grid grid-cols-[1fr_1fr_100px_120px_100px_120px] gap-3 items-center py-2 border-b text-sm">
      <div className="truncate" title={filename}>{filename}</div>
      <div className="text-muted-foreground" title={job_id}>{shortId}</div>
      <div className="uppercase text-xs font-medium">{status}</div>
      <div className="text-muted-foreground">{elapsed_sec ? `${elapsed_sec.toFixed(1)}s` : '-'}</div>
      <div className="text-muted-foreground">{schema_ok === true ? 'OK' : schema_ok === false ? 'FAIL' : '-'}</div>
      <div className="text-muted-foreground">{oc}</div>
      <div className="col-span-6 flex gap-2 pt-2">
        <Button size="sm" variant="outline" onClick={()=>onView(job_id)}>View</Button>
        {status === 'done' && (
          <a className="inline-flex items-center" href={`${API_URL}/jobs/${job_id}/result`} target="_blank" rel="noreferrer">
            <Button size="sm">Download JSON</Button>
          </a>
        )}
      </div>
    </div>
  );
}

export default function JobsDashboard() {
  const [jobs, setJobs] = React.useState([]);
  const [selected, setSelected] = React.useState(null);
  const [selectedData, setSelectedData] = React.useState(null);

  const load = async () => {
    try {
      const r = await fetch(`${API_URL}/jobs`);
      const j = await r.json();
      setJobs(j.jobs || []);
    } catch (e) {
      console.error('jobs load error', e);
    }
  };

  React.useEffect(() => {
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, []);

  const onView = async (job_id) => {
    setSelected(job_id);
    setSelectedData(null);
    try {
      const r = await fetch(`${API_URL}/jobs/${job_id}`);
      const j = await r.json();
      setSelectedData(j);
    } catch (e) {
      console.error('job view error', e);
    }
  };

  return (
    <div className="h-full grid grid-rows-[auto_1fr]">
      <div className="p-4 border-b">
        <Card>
          <CardHeader>
            <CardTitle>Extraction Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-[1fr_1fr_100px_120px_100px_120px] gap-3 text-xs text-muted-foreground border-b pb-2">
              <div>File</div>
              <div>Job</div>
              <div>Status</div>
              <div>Elapsed</div>
              <div>Schema</div>
              <div>Confidence</div>
            </div>
            <ScrollArea className="max-h-[50vh] mt-2">
              {jobs.length === 0 ? (
                <div className="text-sm text-muted-foreground">No jobs yet.</div>
              ) : (
                jobs.map(job => (
                  <JobRow key={job.job_id} job={job} onView={onView} />
                ))
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
      <div className="p-4">
        {selected ? (
          <Card>
            <CardHeader>
              <CardTitle>Job Details: {selected}</CardTitle>
            </CardHeader>
            <CardContent>
              {!selectedData ? (
                <div className="text-sm text-muted-foreground">Loading…</div>
              ) : (
                <pre className="text-xs whitespace-pre-wrap break-words max-h-[40vh] overflow-auto bg-muted/30 p-3 rounded">{JSON.stringify(selectedData, null, 2)}</pre>
              )}
            </CardContent>
          </Card>
        ) : (
          <div className="text-sm text-muted-foreground">Select a job to view details.</div>
        )}
      </div>
    </div>
  );
}

