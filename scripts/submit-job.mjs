#!/usr/bin/env node
// Simple CLI to submit an EntryDetail job to the local backend and print a summary

const API = process.env.API_BASE_URL || 'http://localhost:5001/api';

async function main() {
  const [,, filename, pagesArg] = process.argv;
  if (!filename) {
    console.error('Usage: scripts/submit-job.mjs <filename-in-uploads> [max_pages=2]');
    process.exit(1);
  }
  const max_pages = pagesArg ? Number(pagesArg) : 2;
  const body = {
    filename,
    max_pages,
    scale: 1.6,
    model: 'gemma3:12b',
    agent_version: 'v1'
  };
  const resp = await fetch(`${API}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  if (!resp.ok) {
    const t = await resp.text();
    console.error('Error:', resp.status, t);
    process.exit(2);
  }
  const json = await resp.json();
  const { job_id, elapsed_sec, local_validation, result } = json;
  console.log('job_id:', job_id);
  console.log('elapsed_sec:', elapsed_sec?.toFixed ? elapsed_sec.toFixed(2) : elapsed_sec);
  console.log('schema_ok:', local_validation?.schema_ok);
  if (result?.meta) {
    console.log('overall_confidence:', result.meta.overall_confidence);
    const miss = result.meta.missing_evidence_paths || [];
    if (miss.length) console.log('missing_evidence_paths:', miss.slice(0, 10), `(+${Math.max(0, miss.length-10)} more)`);
  }
  // Print data top-level keys for quick inspection
  const keys = Object.keys(result?.data || {});
  console.log('data keys:', keys.join(', '));
}

main().catch(err => {
  console.error(err);
  process.exit(3);
});

