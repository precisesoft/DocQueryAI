import json
import os
import sys
from datetime import datetime

import boto3
from botocore.config import Config


def pick_chat_model(models, preferred=None):
    # Prefer an override if available and in the list
    if preferred:
        for m in models:
            if m.get('modelId') == preferred:
                return preferred
    # Try common high‑quality instruct models if present
    candidates = [
        'anthropic.claude-3-5-sonnet-20240620-v1:0',
        'anthropic.claude-3-5-haiku-20241022-v1:0',
        'meta.llama3-70b-instruct-v1:0',
        'mistral.mistral-large-2407-v1:0',
        'cohere.command-r-plus-v1:0',
    ]
    ids = {m.get('modelId') for m in models}
    for cid in candidates:
        if cid in ids:
            return cid
    # Fallback: first text-capable model
    for m in models:
        if 'TEXT' in (m.get('outputModalities') or []):
            return m.get('modelId')
    return None


def list_foundation_models(region):
    bedrock = boto3.client('bedrock', region_name=region)
    resp = bedrock.list_foundation_models()
    return resp.get('modelSummaries', [])


def test_converse(region, model_id):
    rt = boto3.client('bedrock-runtime', region_name=region, config=Config(retries={'max_attempts': 3}))
    messages = [
        {"role": "user", "content": [{"text": "In one sentence, say hello from Bedrock."}]}
    ]
    out = rt.converse(
        modelId=model_id,
        messages=messages,
        inferenceConfig={"maxTokens": 128, "temperature": 0.2},
    )
    parts = out.get('output', {}).get('message', {}).get('content', [])
    text = ''.join(p.get('text', '') for p in parts)
    return text.strip()


def test_converse_stream(region, model_id):
    rt = boto3.client('bedrock-runtime', region_name=region, config=Config(retries={'max_attempts': 3}))
    messages = [{"role": "user", "content": [{"text": "Stream three short words: one two three."}]}]
    acc = []
    resp = rt.converse_stream(
        modelId=model_id,
        messages=messages,
        inferenceConfig={"maxTokens": 64, "temperature": 0.0},
    )
    stream = resp.get('stream')
    for event in stream:  # event stream yields dicts with a single key
        if 'contentBlockDelta' in event:
            delta = event['contentBlockDelta'].get('delta', {})
            t = delta.get('text')
            if t:
                acc.append(t)
        elif 'messageStop' in event:
            break
    try:
        close = getattr(stream, 'close', None)
        if callable(close):
            close()
    except Exception:
        pass
    return ''.join(acc).strip()


def test_embedding(region, embedding_model_id, text="Bedrock embeddings quick check"):
    rt = boto3.client('bedrock-runtime', region_name=region)
    body = json.dumps({"inputText": text, "dimensions": 1024})
    resp = rt.invoke_model(modelId=embedding_model_id, body=body)
    payload = json.loads(resp['body'].read())
    emb = payload.get('embedding') or payload.get('embeddings')
    return emb


def main():
    region = os.getenv('AWS_REGION') or os.getenv('BEDROCK_REGION') or 'us-east-1'
    pref_chat = os.getenv('BEDROCK_TEST_CHAT_MODEL_ID')
    emb_model = os.getenv('BEDROCK_EMBEDDING_MODEL_ID', 'amazon.titan-embed-text-v2:0')

    result = {
        'ts': datetime.utcnow().isoformat() + 'Z',
        'region': region,
        'models': {},
        'chat': {},
        'embedding': {},
    }

    try:
        models = list_foundation_models(region)
        result['models']['count'] = len(models)
        result['models']['sample'] = [m.get('modelId') for m in models[:10]]
        chat_model = pick_chat_model(models, pref_chat)
        result['models']['chosen_chat_model'] = chat_model
        if not chat_model:
            print(json.dumps(result, indent=2))
            print('No suitable chat model found in region; grant access or change region.', file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        result['models']['error'] = str(e)
        print(json.dumps(result, indent=2))
        raise

    # Converse (non-stream)
    try:
        text = test_converse(region, chat_model)
        result['chat']['converse_text'] = text
        result['chat']['ok'] = bool(text)
    except Exception as e:
        result['chat']['error_converse'] = str(e)

    # Converse stream
    try:
        text_s = test_converse_stream(region, chat_model)
        result['chat']['converse_stream_text'] = text_s
        result['chat']['stream_ok'] = bool(text_s)
    except Exception as e:
        result['chat']['error_stream'] = str(e)

    # Embedding
    try:
        emb = test_embedding(region, emb_model)
        result['embedding']['dims'] = len(emb) if emb else 0
        result['embedding']['ok'] = bool(emb)
    except Exception as e:
        result['embedding']['error'] = str(e)

    out_dir = os.path.join('tmp')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'bedrock_smoke_results.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    if not (result['chat'].get('ok') and result['chat'].get('stream_ok') and result['embedding'].get('ok')):
        sys.exit(2)


if __name__ == '__main__':
    main()
