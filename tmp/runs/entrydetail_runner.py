import os
import json
import time
import base64
import hashlib
from datetime import datetime, timezone
import uuid

import requests
import fitz  # PyMuPDF
from PyPDF2 import PdfReader


OLLAMA_NATIVE_API = os.environ.get("OLLAMA_NATIVE_API", "http://localhost:11434/api")
MODEL = os.environ.get("VISION_MODEL_NAME", "gemma3:12b")
AGENT_VERSION = os.environ.get("AGENT_VERSION", "v1")


def utcnow_iso():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def render_pdf_to_images_b64(file_path: str, scale: float = 1.6, max_pages: int = 2):
    images_b64 = []
    doc = fitz.open(file_path)
    pages = range(min(max_pages, len(doc)))
    mat = fitz.Matrix(scale, scale)
    for i in pages:
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        png_bytes = pix.tobytes("png")
        images_b64.append(base64.b64encode(png_bytes).decode("utf-8"))
    doc.close()
    return images_b64


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def load_text(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def format_schema_wrapper(inner_schema: dict = None):
    # Inline schema to enforce the wrapper; inner data object validated separately if desired
    return {
        "type": "object",
        "required": ["schema_id", "schema_version", "data", "meta"],
        "properties": {
            "schema_id": {"type": "string", "const": "EntryDetailExtraction"},
            "schema_version": {"type": "string", "const": "1.0"},
            "data": inner_schema if inner_schema else {"type": "object"},
            "meta": {
                "type": "object",
                "required": ["agent_version", "model", "generated_at", "job_id", "overall_confidence", "validation"],
                "properties": {
                    "agent_version": {"type": "string"},
                    "model": {"type": "string"},
                    "generated_at": {"type": "string"},
                    "job_id": {"type": "string"},
                    "overall_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "field_confidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["path", "confidence"],
                            "properties": {
                                "path": {"type": "string"},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                            },
                            "additionalProperties": False
                        }
                    },
                    "field_evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["path", "evidence"],
                            "properties": {
                                "path": {"type": "string"},
                                "evidence": {
                                    "type": "array",
                                    "minItems": 0,
                                    "maxItems": 3,
                                    "items": {
                                        "type": "object",
                                        "required": ["page", "bbox"],
                                        "properties": {
                                            "page": {"type": "integer", "minimum": 1},
                                            "bbox": {
                                                "type": "object",
                                                "required": ["x", "y", "w", "h"],
                                                "properties": {
                                                    "x": {"type": "number", "minimum": 0, "maximum": 1},
                                                    "y": {"type": "number", "minimum": 0, "maximum": 1},
                                                    "w": {"type": "number", "minimum": 0, "maximum": 1},
                                                    "h": {"type": "number", "minimum": 0, "maximum": 1}
                                                },
                                                "additionalProperties": False
                                            }
                                        },
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "additionalProperties": False
                        }
                    },
                    "validation": {
                        "type": "object",
                        "required": ["schema_ok"],
                        "properties": {
                            "schema_ok": {"type": "boolean"},
                            "missing_required": {"type": "array", "items": {"type": "string"}},
                            "warnings": {"type": "array", "items": {"type": "string"}}
                        },
                        "additionalProperties": False
                    }
                },
                "additionalProperties": False
            }
        },
        "additionalProperties": False
    }


def local_validate_entrydetail(data_obj):
    report = {"schema_ok": True, "missing_required": [], "warnings": []}

    # top-level required fields per our schema
    required_top = [
        "entryTypeCode", "operType", "mnlFileInd", "entrdThruPortId",
        "sbmsnDate", "lines", "entryAddress", "uspsContentReviewedAcceptedFlag"
    ]
    for k in required_top:
        if k not in data_obj or data_obj[k] in (None, ""):
            report["missing_required"].append(k)

    # entryAddress exactly 2
    addrs = data_obj.get("entryAddress", []) or []
    if not isinstance(addrs, list) or len(addrs) != 2:
        report["warnings"].append("entryAddress should contain exactly 2 records")
        if len(addrs) < 2:
            report["missing_required"].append("entryAddress[2]")

    # lines >= 1 and each line has quantity exactly 2
    lines = data_obj.get("lines", []) or []
    if not isinstance(lines, list) or len(lines) < 1:
        report["missing_required"].append("lines[1]")
    for i, line in enumerate(lines):
        qty = (line or {}).get("quantity", []) or []
        if len(qty) != 2:
            report["warnings"].append(f"line[{i}].quantity should contain exactly 2 records")

        # minima checks
        total_qty = (line or {}).get("totalQty")
        if isinstance(total_qty, (int, float)) and total_qty < 1.0:
            report["warnings"].append(f"line[{i}].totalQty < 1.0 (min)")
        value_amt = (line or {}).get("valueGoodsAmt")
        if isinstance(value_amt, (int, float)) and value_amt < 0.01:
            report["warnings"].append(f"line[{i}].valueGoodsAmt < 0.01 (min)")

    report["schema_ok"] = len(report["missing_required"]) == 0
    return report


def run_job(pdf_path: str, out_dir: str, max_pages: int = 2):
    ensure_dir(out_dir)
    meta_doc = {
        "filename": os.path.basename(pdf_path),
        "sha256": sha256_file(pdf_path),
        "page_count": len(PdfReader(pdf_path).pages)
    }
    with open(os.path.join(out_dir, 'doc_meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta_doc, f, indent=2)

    # images
    t0 = time.time()
    images = render_pdf_to_images_b64(pdf_path, scale=1.6, max_pages=max_pages)

    # prompts
    sys_prompt = load_text('data/derived/entrydetail.system.txt')
    user_guidance = load_text('data/derived/entrydetail.user-guidance.txt')
    today = datetime.utcnow().date().isoformat()
    job_id = str(uuid.uuid4())

    user_instructions = (
        "You must return the wrapper object with keys schema_id=s 'EntryDetailExtraction', schema_version='1.0', "
        "data (EntryDetail), and meta (metadata). "
        f"Set meta.agent_version='{AGENT_VERSION}', meta.model='{MODEL}', meta.generated_at='{utcnow_iso()}', meta.job_id='{job_id}'. "
        "Set meta.validation with schema_ok=true/false and missing_required/warnings as needed. "
        f"Use today's date for fields that require it: {today}. "
        f"Document: filename={meta_doc['filename']}, page_count={meta_doc['page_count']}. "
    )

    prompt = sys_prompt + "\n\n" + user_guidance + "\n\n" + user_instructions

    # structured output (wrapper only)
    # Use wrapper-only grammar enforcement; inner data will be steered by prompt skeleton
    fmt = format_schema_wrapper()

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "images": images,
        "format": fmt,
        "stream": False,
        "options": {"temperature": 0.2}
    }

    # store request without raw images
    redacted = dict(payload)
    redacted['images'] = [f"<base64 {len(img)} chars>" for img in images]
    with open(os.path.join(out_dir, 'request.json'), 'w', encoding='utf-8') as f:
        json.dump(redacted, f, indent=2)

    # call model (allow long warmup)
    r = requests.post(f"{OLLAMA_NATIVE_API}/generate", json=payload, timeout=900)
    elapsed = time.time() - t0
    with open(os.path.join(out_dir, 'raw_response.json'), 'w', encoding='utf-8') as f:
        f.write(r.text)

    result = {
        'status_code': r.status_code,
        'elapsed_sec': elapsed,
        'ok': False,
        'error': None,
        'job_id': job_id
    }

    try:
        j = r.json()
        resp_text = j.get('response', '')
        with open(os.path.join(out_dir, 'response.txt'), 'w', encoding='utf-8') as f:
            f.write(resp_text)
        obj = json.loads(resp_text)
        result['ok'] = True
        result['model'] = j.get('model')
        result['done'] = j.get('done')
        result['done_reason'] = j.get('done_reason')

        # write result pieces
        with open(os.path.join(out_dir, 'result.wrapper.json'), 'w', encoding='utf-8') as f:
            json.dump(obj, f, indent=2)
        data_obj = obj.get('data', {})
        with open(os.path.join(out_dir, 'result.data.json'), 'w', encoding='utf-8') as f:
            json.dump(data_obj, f, indent=2)

        # local validation
        local_val = local_validate_entrydetail(data_obj)
        with open(os.path.join(out_dir, 'local_validation.json'), 'w', encoding='utf-8') as f:
            json.dump(local_val, f, indent=2)
        result['local_validation'] = local_val

        # meta post-processing: cap confidence when evidence missing; compute overall_confidence if absent
        meta = obj.setdefault('meta', {})
        fc = meta.get('field_confidence', []) or []
        fe = meta.get('field_evidence', []) or []
        # Build set of paths with evidence
        paths_with_evidence = set()
        for item in fe:
            try:
                p = item.get('path')
                ev = item.get('evidence', [])
                if p and isinstance(ev, list) and len(ev) > 0:
                    paths_with_evidence.add(p)
            except Exception:
                pass
        # Cap confidences for items without evidence
        for item in fc:
            try:
                p = item.get('path')
                c = float(item.get('confidence', 0))
                if p not in paths_with_evidence and c > 0.5:
                    item['confidence'] = 0.5
            except Exception:
                continue
        # Compute overall confidence if missing
        if fc:
            try:
                vals = [float(x.get('confidence', 0)) for x in fc]
                overall = sum(vals) / max(len(vals), 1)
                meta.setdefault('overall_confidence', overall)
            except Exception:
                meta.setdefault('overall_confidence', 0.5)
        else:
            meta.setdefault('overall_confidence', 0.5)

        # persist updated wrapper
        with open(os.path.join(out_dir, 'result.wrapper.json'), 'w', encoding='utf-8') as f:
            json.dump(obj, f, indent=2)
    except Exception as e:
        result['error'] = f'parse error: {e}'

    with open(os.path.join(out_dir, 'summary.json'), 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    return result


def main():
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    base_run_dir = f"/app/tmp/runs/entrydetail_{ts}"
    ensure_dir(base_run_dir)

    docs = [
        '/app/uploads/DHL Generated Sample 01.pdf',
        '/app/uploads/amj58187ups-7a.pdf',
        '/app/uploads/AMJ64528UPS-4 cont..pdf'
    ]

    results = {}
    for pdf in docs:
        name = os.path.basename(pdf)
        out_dir = os.path.join(base_run_dir, name.replace(' ', '_'))
        print(f"Running: {name}")
        try:
            res = run_job(pdf, out_dir, max_pages=2)
        except Exception as e:
            res = {'status_code': -1, 'ok': False, 'error': str(e)}
        results[name] = res
        print(f" -> {res.get('status_code')} ok={res.get('ok')} elapsed={res.get('elapsed_sec')} error={res.get('error')}")

    with open(os.path.join(base_run_dir, 'run_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print("Run dir:", base_run_dir)


if __name__ == '__main__':
    main()
