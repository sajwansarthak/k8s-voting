# K8s Voting App — Minikube Edition (Free, From Scratch)

A self-contained rebuild of the classic "voting app" microservices demo — every
service written from scratch here, no external repo needed. Runs entirely on
Minikube on your own machine. Cost: $0.

## What's in this project

```
voting-app/
├── vote/                     # Python (Flask) — lets you vote Cats vs Dogs
├── worker/                   # Python — reads votes from Redis, writes to Postgres
├── result/                   # Node.js (Express + Socket.IO) — live results page
├── k8s-specifications/       # Kubernetes manifests for all services
├── argocd/                   # Argo CD Application manifest (GitOps, optional)
└── build-images.sh           # builds all 3 images inside Minikube's Docker
```

Architecture: **vote** (web UI) → **Redis** (queue) → **worker** (consumer) →
**Postgres** (storage) → **result** (live dashboard, via websockets).

Note: the original Docker sample project's worker is written in .NET. This
version's worker is Python instead, purely to keep the whole stack buildable
with nothing but Docker — functionally it does the same job.

---

## 1. Prerequisites

Install Docker, kubectl, and Minikube.

**Linux**
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker

curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
```

**macOS**
```bash
brew install docker kubectl minikube
```

**Windows (PowerShell as Admin)**
```powershell
choco install docker-desktop kubernetes-cli minikube -y
```

---

## 2. Start Minikube

```bash
minikube start --cpus=4 --memory=8192 --driver=docker
kubectl get nodes      # should show minikube node "Ready"
```

(Tighter on resources? `--cpus=2 --memory=4096` is enough for this app.)

---

## 3. Build the app images

Minikube runs its own internal Docker daemon. Building your images there
means Kubernetes can use them immediately — no registry, no `docker push`,
no AWS account required.

```bash
cd voting-app
chmod +x build-images.sh
./build-images.sh
```

This builds `voting-app-vote`, `voting-app-worker`, and `voting-app-result`
directly inside Minikube.

---

## 4. Deploy — Option A: plain kubectl (fastest, no git needed)

```bash
kubectl apply -f k8s-specifications/
```

Check everything is up:
```bash
kubectl get pods
kubectl get svc
```

Open the app:
```bash
minikube service vote     # opens the voting page
minikube service result   # opens the live results page
```

Vote a few times on the `vote` page, then check `result` — it updates live.

---

## 5. Deploy — Option B: Argo CD (GitOps, closer to the original guide)

Skip this if Option A is all you need. Use this if you specifically want the
Argo CD workflow.

### 5.1 Push this project to your own git repo
Argo CD pulls from git, not your local disk, so:
```bash
git init
git add .
git commit -m "voting app"
git remote add origin https://github.com/<you>/<your-repo>.git
git push -u origin main
```
Then edit `argocd/voting-app-application.yaml` and replace the `repoURL`
placeholder with your actual repo URL.

### 5.2 Install Argo CD
```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=available --timeout=300s deployment --all -n argocd
```

Get the admin password:
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo
```

Open the UI:
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```
Visit `https://localhost:8080`, log in as `admin`.

### 5.3 Register the app
```bash
kubectl apply -f argocd/voting-app-application.yaml
```
Argo CD will pull `k8s-specifications/` from your repo and sync it
automatically. Because images are built locally into Minikube's Docker (not
pulled from a registry), this works fine for a local demo — just re-run
`build-images.sh` after any code change, then let Argo CD re-sync (or
`kubectl rollout restart deployment vote worker result`).

---

## 6. Kubernetes Dashboard (optional, visual pod/service browser)

```bash
minikube addons enable dashboard
minikube addons enable metrics-server
minikube dashboard
```

---

## 7. Observability — Prometheus & Grafana (optional)

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
kubectl create namespace monitoring
helm install kube-prom prometheus-community/kube-prometheus-stack -n monitoring
```

```bash
kubectl port-forward svc/kube-prom-grafana -n monitoring 3000:80
kubectl get secret kube-prom-grafana -n monitoring -o jsonpath="{.data.admin-password}" | base64 -d; echo
```
Login at `http://localhost:3000` with `admin` / the password above.

---

## 8. Cleanup

```bash
minikube stop     # pause, keep state
minikube delete    # remove cluster completely
```

---

## Troubleshooting

- **Pods stuck in `ImagePullBackOff`**: you skipped step 3, or ran
  `docker build` without `eval $(minikube docker-env)` first — the images
  need to exist inside Minikube's own Docker, not your host's.
- **`worker` crashlooping**: check `kubectl logs deployment/worker` — usually
  means Postgres isn't ready yet; the worker retries automatically so it
  should self-heal within a few seconds.
- **`minikube service` hangs on Windows/WSL**: run `minikube tunnel` in a
  separate terminal instead, then use the ClusterIP + NodePort directly.
