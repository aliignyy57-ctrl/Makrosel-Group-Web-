"""Generate ELISA kit images via Kie.ai API (gpt-image/1.5-text-to-image)."""
import urllib.request, json, time, os, sys

KEY = os.environ.get('KIE_API_KEY', '')
if not KEY:
    print('ERROR: KIE_API_KEY not set')
    sys.exit(1)

BASE = 'https://api.kie.ai'
OUT = '/Users/mac/Desktop/makrosel/assets/images/elisa/'
os.makedirs(OUT, exist_ok=True)

CATEGORIES = [
    ('human',   'Professional laboratory ELISA test kit for human diagnostics, medical blue tones, clean white background, scientific product photography, 96-well microplate, antibody vials, pipette'),
    ('mouse',   'Laboratory mouse ELISA immunoassay kit, scientific research, blue medical tones, white background, professional product photo, 96-well plate, pipette, laboratory equipment'),
    ('rat',     'Laboratory rat ELISA immunoassay kit, scientific research, blue tones, clean white background, 96-well plate, pipette, professional laboratory product photography'),
    ('rabbit',  'Rabbit ELISA kit laboratory immunology research, medical blue tones, white background, scientific product photography, antibody detection kit, microplate'),
    ('bovine',  'Bovine cattle ELISA kit veterinary diagnostics, blue medical tones, white background, professional scientific photography, immunoassay microplate, laboratory'),
    ('sheep',   'Sheep ovine ELISA kit veterinary laboratory, blue tones, clean white background, scientific product photo, immunoassay detection kit, 96-well plate'),
    ('goat',    'Goat caprine ELISA kit veterinary research, medical blue tones, white background, professional laboratory photography, 96-well microplate, scientific'),
    ('horse',   'Horse equine ELISA kit veterinary diagnostics, blue tones, white background, scientific product photography, immunoassay research kit, laboratory'),
    ('chicken', 'Chicken avian ELISA kit poultry research, laboratory blue tones, clean white background, scientific product photo, antibody detection microplate, professional'),
    ('dog',     'Canine dog ELISA kit veterinary diagnostics, blue medical tones, white background, professional scientific photography, immunoassay detection, laboratory'),
    ('cat',     'Feline cat ELISA kit veterinary laboratory, blue tones, clean white background, scientific product photography, immunoassay kit, 96-well plate'),
    ('pig',     'Porcine pig ELISA kit veterinary research, medical blue tones, white background, professional laboratory photo, 96-well microplate immunoassay, scientific'),
    ('monkey',  'Primate monkey ELISA kit biomedical research, blue tones, clean white background, scientific product photography, immunoassay laboratory, medical'),
]

def api(method, path, data=None):
    headers = {
        'Authorization': f'Bearer {KEY}',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0',
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode()), r.status
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read().decode()), e.code
        except: return {}, e.code
    except Exception as e:
        return {'err': str(e)}, 0

def download_img(url, path):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        with open(path, 'wb') as f:
            f.write(r.read())

# Doğru payload - playgroundData şemasından
def make_payload(prompt):
    return {
        'model': 'gpt-image/1.5-text-to-image',
        'callBackUrl': 'https://example.com/cb',
        'input': {
            'prompt': prompt,
            'aspect_ratio': '3:2',
            'quality': 'medium',
        }
    }

# Önce tek test yap
print('=== Testing payload ===')
test_resp, test_code = api('POST', '/api/v1/jobs/createTask', make_payload('test ELISA kit blue'))
print(f'Test: {test_code} → {json.dumps(test_resp, ensure_ascii=False)[:200]}')

if test_resp.get('code') not in (200,):
    print('\nTrying alternate aspect_ratio values...')
    for ar in ['1:1', '16:9', '4:3', '3:2', '2:3', '9:16', 'square', 'landscape']:
        r, c = api('POST', '/api/v1/jobs/createTask', {
            'model': 'gpt-image/1.5-text-to-image',
            'callBackUrl': 'https://example.com/cb',
            'input': {'prompt': 'test', 'aspect_ratio': ar, 'quality': 'medium'}
        })
        print(f'  aspect_ratio={ar:12s} → {r.get("msg","?")} | data={str(r.get("data",""))[:60]}')
        time.sleep(1)
    sys.exit(0)

# Task ID çıkar
def extract_task_id(resp_data):
    if isinstance(resp_data, str):
        return resp_data
    if isinstance(resp_data, dict):
        for k in ('taskId', 'task_id', 'id', 'requestId'):
            if resp_data.get(k):
                return resp_data[k]
    return None

# Görevleri gönder
task_ids = {}
print(f'\n=== Submitting {len(CATEGORIES)} image tasks ===')
for name, prompt in CATEGORIES:
    resp, code = api('POST', '/api/v1/jobs/createTask', make_payload(prompt))
    msg = resp.get('msg', '?')
    data = resp.get('data')
    task_id = extract_task_id(data)
    status = '✓' if resp.get('code') == 200 else '✗'
    print(f'  {status} {name:10s}: {msg} | taskId={task_id}')
    if task_id:
        task_ids[name] = task_id
    time.sleep(1.5)  # rate limit için

if not task_ids:
    print('No tasks created successfully.')
    sys.exit(1)

print(f'\n=== Polling {len(task_ids)} tasks (max 5 min) ===')
MAX_WAIT = 300
POLL_INTERVAL = 10
start = time.time()
done = set()
saved = {}

while len(done) < len(task_ids) and (time.time() - start) < MAX_WAIT:
    for name, tid in task_ids.items():
        if name in done:
            continue
        resp, code = api('GET', f'/api/v1/jobs/recordInfo?taskId={tid}')
        data = resp.get('data', {}) or {}
        status = data.get('status') or data.get('state') or '?'

        if status in ('SUCCESS', 'success', 'COMPLETED', 'completed', 2, '2', 'FINISHED'):
            # Görsel URL bul
            img_url = None
            for path_keys in [
                ['response', 'imageUrl'], ['imageUrl'], ['url'],
                ['output', 'url'], ['result', 'url'], ['images', 0, 'url'],
                ['response', 'images', 0, 'url'],
            ]:
                obj = data
                for k in path_keys:
                    if isinstance(obj, dict):
                        obj = obj.get(k)
                    elif isinstance(obj, list) and isinstance(k, int):
                        obj = obj[k] if k < len(obj) else None
                    else:
                        obj = None
                    if obj is None:
                        break
                if isinstance(obj, str) and obj.startswith('http'):
                    img_url = obj
                    break

            if img_url:
                # Uzantıyı URL'den belirle
                ext = 'jpg' if 'jpg' in img_url.lower() or 'jpeg' in img_url.lower() else \
                      'png' if 'png' in img_url.lower() else 'jpg'
                out_path = os.path.join(OUT, f'{name}.{ext}')
                try:
                    download_img(img_url, out_path)
                    sz = os.path.getsize(out_path)
                    saved[name] = out_path
                    print(f'  ✓ {name} saved ({sz//1024}KB) → {out_path}')
                except Exception as e:
                    print(f'  ✗ {name} download error: {e}')
                done.add(name)
            else:
                print(f'  ! {name} SUCCESS but no image URL. Full data: {json.dumps(data, ensure_ascii=False)[:300]}')
                done.add(name)

        elif status in ('FAILED', 'failed', 'ERROR', 'error', -1, '-1'):
            print(f'  ✗ {name} FAILED: {data.get("errorMessage") or data.get("error") or "?"}')
            done.add(name)

        elif status in ('PENDING', 'pending', 'PROCESSING', 'processing', 0, '0', 1, '1'):
            pass  # devam ediyor

        else:
            print(f'  ? {name} unknown status: {status} | {json.dumps(data, ensure_ascii=False)[:100]}')

    pending = [n for n in task_ids if n not in done]
    if pending:
        elapsed = int(time.time() - start)
        print(f'  [{elapsed}s] Waiting: {pending}')
        time.sleep(POLL_INTERVAL)

print(f'\n=== Results: {len(saved)}/{len(task_ids)} images saved ===')
for name, path in saved.items():
    print(f'  {name}: {path}')
