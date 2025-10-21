import os
import json
import time
import base64
import hashlib
from datetime import datetime

import requests
import fitz  # PyMuPDF
from PyPDF2 import PdfReader


OLLAMA_NATIVE_API = os.environ.get("OLLAMA_NATIVE_API", "http://localhost:11434/api")
MODEL = os.environ.get("VISION_MODEL_NAME", "gemma3:12b")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def render_pdf_to_images_b64(file_path: str, scale: float = 1.75, max_pages: int = 1):
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


def load(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def run_job(pdf_path: str, out_dir: str, max_pages: int = 1):
    ensure_dir(out_dir)
    meta = {}
    meta['filename'] = os.path.basename(pdf_path)
    meta['sha256'] = sha256_file(pdf_path)
    meta['page_count'] = len(PdfReader(pdf_path).pages)

    # Save meta
    with open(os.path.join(out_dir, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)

    # Render images
    t0 = time.time()
    images = render_pdf_to_images_b64(pdf_path, scale=1.75, max_pages=max_pages)
    with open(os.path.join(out_dir, 'images.count'), 'w') as f:
        f.write(str(len(images)))

    system_prompt = load('/app/tmp/prompts/shipping_label.system.txt')
    schema = load_json('/app/tmp/contracts/shipping_label.v1.schema.json')

    user_instructions = (
        "Fill the contract for this document. Set doc.filename and doc.page_count exactly as provided. "
        "Use schema_id='shipping_label' and schema_version='1.0'. "
        "Use null when a field is absent. Provide bbox and page for each non-null field."
        f"\nDoc metadata: filename={meta['filename']}; page_count={meta['page_count']}.\n"
    )

    prompt = system_prompt + "\n\n" + user_instructions

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "images": images,
        "format": schema,
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }

    # Save prompt/payload skeleton
    with open(os.path.join(out_dir, 'request.json'), 'w', encoding='utf-8') as f:
        req_copy = dict(payload)
        req_copy['images'] = [f"<base64 {len(img)} chars>" for img in images]
        f.write(json.dumps(req_copy, indent=2))

    # Call model
    r = requests.post(f"{OLLAMA_NATIVE_API}/generate", json=payload, timeout=600)
    elapsed = time.time() - t0

    with open(os.path.join(out_dir, 'raw_response.json'), 'w', encoding='utf-8') as f:
        f.write(r.text)

    result = {
        'status_code': r.status_code,
        'elapsed_sec': elapsed,
        'ok': False,
        'error': None
    }

    try:
        j = r.json()
        result['ok'] = True
        result['model'] = j.get('model')
        result['done'] = j.get('done')
        result['done_reason'] = j.get('done_reason')
        resp_text = j.get('response', '')
        with open(os.path.join(out_dir, 'response.txt'), 'w', encoding='utf-8') as f:
            f.write(resp_text)
        try:
            parsed = json.loads(resp_text)
            with open(os.path.join(out_dir, 'result.json'), 'w', encoding='utf-8') as f:
                json.dump(parsed, f, indent=2)
            result['parsed'] = True
        except Exception as e:
            result['parsed'] = False
            result['error'] = f'parse error: {e}'
    except Exception as e:
        result['error'] = f'bad json from service: {e}'

    with open(os.path.join(out_dir, 'summary.json'), 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    return result


def main():
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    base_run_dir = f"/app/tmp/runs/{ts}"
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
        res = run_job(pdf, out_dir, max_pages=1)
        results[name] = res
        print(f" -> {res['status_code']} parsed={res.get('parsed')} elapsed={res['elapsed_sec']:.1f}s error={res.get('error')}")

    with open(os.path.join(base_run_dir, 'run_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print("Run dir:", base_run_dir)


if __name__ == '__main__':
    main()
