"""Exercise the local Docker deployment and record actual results."""
import http.cookiejar
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
base = 'http://127.0.0.1:8090'
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
results = []

def record(message):
    print(message, flush=True)
    results.append(message)

def get(path):
    with opener.open(base + path, timeout=5) as response:
        return response.status, response.read().decode()

def post(path, data):
    request = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode())
    with opener.open(request, timeout=5) as response:
        return response.status, response.read().decode()

def wait():
    for attempt in range(30):
        try:
            status, body = get('/healthz')
            if status == 200:
                return json.loads(body)
        except OSError:
            time.sleep(1)
    raise RuntimeError('App did not become healthy')

record('Actual Docker app verification: ' + datetime.now(timezone.utc).isoformat())
health = wait()
record('GET /healthz -> HTTP 200: ' + json.dumps(health, sort_keys=True))
status, page = get('/')
assert status == 200 and 'daybook' in page
record('GET / -> HTTP 200, rendered task tracker HTML')
token = re.search(r'name="csrf_token" value="([a-f0-9]+)"', page).group(1)
existing = json.loads(get('/api/tasks')[1])['tasks']
if not existing:
    for title in ['Build a Python app in WSL', 'Deploy the image on the second laptop', 'Verify persistent storage']:
        post('/tasks', {'title':title, 'csrf_token':token})
    first = json.loads(get('/api/tasks')[1])['tasks'][0]
    post(f'/tasks/{first["id"]}/toggle', {'csrf_token':token})
    record('Created starter tasks and completed the first task using real HTTP forms.')
else:
    record('Existing task records reused; no duplicate starter tasks created.')
before = json.loads(get('/api/tasks')[1])['tasks']
assert len(before) >= 3
record('GET /api/tasks -> ' + json.dumps(before, sort_keys=True))
subprocess.run(['wsl','-d','Ubuntu','--exec','docker','restart','python-webapp-local'],check=True)
wait()
after = json.loads(get('/api/tasks')[1])['tasks']
assert before == after
record('Docker container restart -> task records persisted unchanged in the named volume.')
(ROOT / 'LIVE-RESULTS.txt').write_text('\n'.join(results) + '\n', encoding='utf-8')
