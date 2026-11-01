"""Verify HTTP access and SQLite persistence across a Kubernetes Pod replacement."""
from pathlib import Path
import subprocess

script = r'''set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
export KUBECONFIG="$HOME/devops-day2/kubeconfig"
PF_PID=''
trap 'if [ -n "$PF_PID" ]; then kill "$PF_PID" 2>/dev/null || true; fi' EXIT
forward() {
  kubectl --context kind-day2 -n python-app port-forward service/daybook 8091:80 > /tmp/daybook-k8s-forward.log 2>&1 &
  PF_PID=$!
}
forward
python3 - <<'PY'
import http.cookiejar, json, re, time, urllib.parse, urllib.request
from pathlib import Path
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
base='http://127.0.0.1:8091'
for _ in range(30):
    try:
        with opener.open(base+'/healthz',timeout=3) as response:
            print('Kubernetes GET /healthz ->',response.status,response.read().decode().strip())
        break
    except OSError:
        time.sleep(1)
else:
    raise RuntimeError('Kubernetes service unavailable')
with opener.open(base) as response:
    token=re.search(r'name="csrf_token" value="([a-f0-9]+)"',response.read().decode()).group(1)
payload=urllib.parse.urlencode({'title':'Verify data survives a Kubernetes Pod replacement','csrf_token':token}).encode()
with opener.open(base+'/tasks',data=payload) as response:
    assert response.status==200
with opener.open(base+'/api/tasks') as response:
    tasks=json.load(response)['tasks']
task=next(t for t in reversed(tasks) if t['title']=='Verify data survives a Kubernetes Pod replacement')
Path('/tmp/daybook-persistence-id').write_text(str(task['id']))
print('Created task through Kubernetes Service:',json.dumps(task,sort_keys=True))
PY
kill "$PF_PID"
wait "$PF_PID" 2>/dev/null || true
PF_PID=''
kubectl --context kind-day2 -n python-app rollout restart deployment/daybook
kubectl --context kind-day2 -n python-app rollout status deployment/daybook --timeout=180s
forward
python3 - <<'PY'
import http.cookiejar,json,re,time,urllib.parse,urllib.request
from pathlib import Path
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
base='http://127.0.0.1:8091'
for _ in range(30):
    try:
        with opener.open(base+'/api/tasks',timeout=3) as response:
            tasks=json.load(response)['tasks']
        break
    except OSError:
        time.sleep(1)
else:
    raise RuntimeError('Replacement Pod unavailable')
task_id=int(Path('/tmp/daybook-persistence-id').read_text())
assert any(t['id']==task_id and t['title']=='Verify data survives a Kubernetes Pod replacement' for t in tasks)
print('PASS: SQLite task persisted across Pod replacement using the persistent volume.')
with opener.open(base) as response:
    token=re.search(r'name="csrf_token" value="([a-f0-9]+)"',response.read().decode()).group(1)
with opener.open(base+f'/tasks/{task_id}/delete',data=urllib.parse.urlencode({'csrf_token':token}).encode()) as response:
    assert response.status==200
print('Removed only the temporary persistence-test task.')
PY
kubectl --context kind-day2 -n python-app get pods,pvc,services
'''
# The raw string keeps Python regexes intact; quotes need no shell escaping on stdin.
script = script.replace('\\"', '"')
result = subprocess.run(['wsl','-d','Ubuntu','--exec','bash','-s'], input=script.encode(), capture_output=True)
output = result.stdout.decode(errors='replace') + '\n' + result.stderr.decode(errors='replace')
print(output)
with (Path(__file__).parent/'KUBERNETES-LIVE-RESULTS.txt').open('a',encoding='utf-8') as file:
    file.write('\nHTTP and Pod-replacement persistence test:\n'+output)
raise SystemExit(result.returncode)
