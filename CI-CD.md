# Automatic deployment to the second laptop

Pushes to `main` run tests inside Docker on GitHub, build a release image tagged
with the Git commit, and upload it as a workflow artifact (retained for 3 days).
The second laptop's runner downloads the same image, loads it into `kind-day2`,
applies `k8s.yaml` with the release image tag, and waits for
`python-app/daybook` to become ready. No registry account is needed.

Pull requests run tests and builds on GitHub only. Only trusted changes should
be pushed to this repository's `main` branch. The deployment runner is registered
only for `MalaniPrince/python-webapp`, with the label `day2-deploy`.

The existing `daybook-data` PVC is preserved. SQLite uses a single replica and
the `Recreate` strategy, so updates have a brief interruption. If a rollout
fails, the script attempts to restore the previous deployment revision.
This does not roll back database schema changes.

Edit code on the first PC, then stage, commit, and push the intended files.
Watch **Actions > Python App CI/CD**. The deployment summary shows the deployed
commit and image. Refresh the app page after deployment completes. Saving files
alone does not trigger deployment.

The second laptop must be awake, WSL and Docker running, and the runner online.
Offline runners leave deployments queued. No inbound public SSH or Kubernetes
endpoint is required. Old Docker/kind images are not automatically pruned;
monitor disk use.

## Runner maintenance (second laptop)

```bash
cd /home/priyanshu/actions-runner-day2
sudo ./svc.sh status
sudo ./svc.sh stop
sudo ./svc.sh start
```

The runner uses `/home/priyanshu/.kube/config` and explicitly selects `kind-day2`.
It can use the installed image-loading helper through passwordless sudo;
arbitrary Docker commands are not granted. The helper checks the image tag and
archive location. Initial privileged setup after runner registration:

```bash
sudo bash /home/priyanshu/daybook-cd-setup/install-runner-service.sh
```
