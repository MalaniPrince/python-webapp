# Daybook: a real Python app you can deploy to the second laptop

A Flask task tracker with a responsive interface, SQLite persistence, and Gunicorn. Add tasks, complete/reopen them, filter them, and delete them. No Docker Hub account is needed for the transfer below.

## What is already verified on THIS laptop

- Local Docker app: **http://localhost:8090**.
- HTTP task creation and completion worked; data survived a Docker restart.
- The same image deployed into this laptop's `kind-day2` cluster.
- The Kubernetes Pod became ready and the persistent volume claim bound.
- A task survived replacement of the Kubernetes Pod.
- Unit tests passed for persistence, validation, CSRF checks, and HTML escaping.

Actual results are in `LIVE-RESULTS.txt` and `KUBERNETES-LIVE-RESULTS.txt`.

**The second laptop deployment has not been executed by the assistant.** SSH reaches it, but this session has no working noninteractive login. Run the transfer below with your normal SSH password. Do not send your password into chat.

## 1. View or modify the source on THIS laptop

The source is in `C:\Users\HP\Desktop\devops\python-webapp`.

Important files:

- `app.py`: Python routes, validation, and database operations.
- `templates/index.html` and `static/style.css`: interface.
- `Dockerfile` and `requirements.txt`: container build and pinned direct dependencies.
- `k8s.yaml`: namespace, single-replica Deployment, Service, and persistent storage.
- `tests/test_app.py`: behavior tests.

For source editing with live reload and a database visible in this project, run:

```powershell
cd C:\Users\HP\Desktop\devops\python-webapp
python dev.py
```

Open **http://localhost:8092**. This development mode uses `data/tasks.sqlite3`, independently of the Docker application's named volume. It starts with its own empty task list. See [database locations and development instructions](DATABASE-AND-DEVELOPMENT.md).

You can run the tests from Windows PowerShell if pytest and Flask are installed:

```powershell
python -m pytest python-webapp/tests -q
```

For a fresh development environment, create a virtual environment and install Flask and pytest there. Gunicorn runs inside the Linux container rather than directly on Windows.

## 2. Transfer the ready-made image to the SECOND laptop

Run these commands in **THIS laptop's Ubuntu WSL**:

```bash
cd /mnt/c/Users/HP/Desktop/devops

scp -P 2222 \
  python-webapp-v1.tar.gz \
  python-webapp-k8s.yaml \
  python-webapp-deploy.sh \
  python-webapp-files.sha256 \
  priyanshu@100.110.248.34:/home/priyanshu/
```

Enter `priyanshu`'s Ubuntu password when prompted. Both Windows Tailscale clients must be connected and SSH forwarding must still work. `scp` uses uppercase `-P` for the port; `ssh` uses lowercase `-p`.

The image contains application code, not the starter tasks stored in this laptop's Docker volume. The second laptop starts with an empty task list.

## 3. Deploy on the SECOND laptop

In the **second laptop's Ubuntu terminal**, run:

```bash
cd /home/priyanshu
sha256sum --check python-webapp-files.sha256
```

Continue only if all three package components listed by the checksum file report `OK` (the checksum file itself is not included in its own checks).

```bash
bash python-webapp-deploy.sh
```

The script asks for sudo if you are not already root. It targets the existing cluster at `/root/devops-day2/kubeconfig`, uses the Ubuntu-installed `/usr/bin/kind` that resolved your earlier crash, loads the image into the nodes, and applies the app's Kubernetes configuration. If kubectl is missing, it downloads and checks a client matching your cluster. It creates a separate namespace, `python-app`, and does not replace the earlier Nginx practice Deployment.

Your cluster can be Kubernetes 1.34.0; it need not match this laptop's Kubernetes version. Both laptops in this session are AMD64, matching the supplied image.

Check the result (run in the second laptop root shell; use `sudo -i` first if necessary):

```bash
export KUBECONFIG=/root/devops-day2/kubeconfig
kubectl --context kind-day2 -n python-app get pods,pvc,services
```

Success criteria: Deployment ready, Pod `1/1 Running`, and PVC `Bound`. These are criteria to check, not claimed output from your second laptop.

## 4. Open the app on the SECOND laptop

In the same root shell, leave this running:

```bash
kubectl --context kind-day2 -n python-app port-forward service/daybook 8090:80
```

Open **http://localhost:8090** in the second laptop's Windows browser. For an HTTP check, use another Ubuntu terminal on that laptop:

```bash
curl http://127.0.0.1:8090/healthz
```

## 5. Open the SECOND laptop's app from THIS laptop

Keep the second laptop's port-forward running. In this laptop's Ubuntu, open a separate terminal and run:

```bash
ssh -p 2222 -N \
  -L 127.0.0.1:18090:127.0.0.1:8090 \
  priyanshu@100.110.248.34
```

Then browse **http://localhost:18090** on this laptop. Port 8090 shows this laptop's local Docker app; port 18090 shows the second laptop's Kubernetes app through SSH. Leave the SSH tunnel open while using it. Stop either temporary forwarding command with Ctrl+C.

## 6. Edit, rebuild, and ship a new version

On THIS laptop WSL, after changing the code:

```bash
cd /mnt/c/Users/HP/Desktop/devops/python-webapp
docker build -t python-webapp:v2 .
docker save python-webapp:v2 | gzip > ../python-webapp-v2.tar.gz
scp -P 2222 ../python-webapp-v2.tar.gz \
  priyanshu@100.110.248.34:/home/priyanshu/
```

On the SECOND laptop root terminal:

```bash
export KUBECONFIG=/root/devops-day2/kubeconfig
docker load -i /home/priyanshu/python-webapp-v2.tar.gz
/usr/bin/kind load docker-image python-webapp:v2 --name day2
kubectl --context kind-day2 -n python-app set image deployment/daybook \
  web=python-webapp:v2
kubectl --context kind-day2 -n python-app rollout status deployment/daybook
```

Restart the temporary port-forward if it stops when the Pod is replaced. Use a fresh image tag for each release. The Docker standalone container keeps running its old image until separately replaced; these update commands target Kubernetes.

## Storage and access

This private lab app has no user accounts: anyone with access to the app can modify its shared task list. Access the second laptop through the existing Tailscale/SSH connection; the instructions don't expose a public web port.

SQLite runs in **one replica** with a persistent volume. Data survives container/Pod replacement, but deleting the PVC or the entire kind cluster can delete it. For a multi-replica application shared across nodes, use a separate database such as PostgreSQL. Back up real data before deleting lab storage.

Official references: [Flask with Gunicorn](https://flask.palletsprojects.com/en/stable/deploying/gunicorn/), [loading local images into kind](https://kind.sigs.k8s.io/docs/user/quick-start/#loading-an-image-into-your-cluster).
