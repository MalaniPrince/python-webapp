#!/usr/bin/env bash
set -euo pipefail

# This targets the second laptop's existing root-owned kind cluster.
if [ "$(id -u)" -ne 0 ]; then
  exec sudo bash "$0" "$@"
fi

PACKAGE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export KUBECONFIG="${DAYBOOK_KUBECONFIG:-/root/devops-day2/kubeconfig}"
KIND_BIN="${KIND_BIN:-/usr/bin/kind}"
test -r "$KUBECONFIG" || { echo "Missing cluster kubeconfig: $KUBECONFIG"; exit 1; }
test -x "$KIND_BIN" || { echo "Missing kind executable: $KIND_BIN"; exit 1; }
test -r "$PACKAGE_DIR/python-webapp-v1.tar.gz"
test -r "$PACKAGE_DIR/python-webapp-k8s.yaml"
docker info >/dev/null

if ! command -v kubectl >/dev/null 2>&1; then
  case "$(uname -m)" in
    x86_64) ARCH=amd64 ;;
    aarch64) ARCH=arm64 ;;
    *) echo "Unsupported architecture"; exit 1 ;;
  esac
  K8S_VERSION=$(docker exec day2-control-plane kubelet --version | awk '{print $2}')
  BASE="https://dl.k8s.io/release/${K8S_VERSION}/bin/linux/${ARCH}"
  CLIENT_DIR=$(mktemp -d)
  trap 'rm -f "$CLIENT_DIR/kubectl" "$CLIENT_DIR/kubectl.sha256"; rmdir "$CLIENT_DIR"' EXIT
  curl -fL --retry 3 -o "$CLIENT_DIR/kubectl" "$BASE/kubectl"
  curl -fL --retry 3 -o "$CLIENT_DIR/kubectl.sha256" "$BASE/kubectl.sha256"
  (cd "$CLIENT_DIR"; echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check)
  install -m 0755 "$CLIENT_DIR/kubectl" /usr/local/bin/kubectl
fi

kubectl --context kind-day2 cluster-info
kubectl --context kind-day2 wait --for=condition=Ready nodes --all --timeout=180s
docker load -i "$PACKAGE_DIR/python-webapp-v1.tar.gz"
"$KIND_BIN" load docker-image python-webapp:v1 --name day2
kubectl --context kind-day2 apply -f "$PACKAGE_DIR/python-webapp-k8s.yaml"
kubectl --context kind-day2 -n python-app rollout status deployment/daybook --timeout=180s
kubectl --context kind-day2 -n python-app get pods,pvc,services

echo
echo 'Deployment ready. To open the application on this laptop, run:'
echo 'export KUBECONFIG=/root/devops-day2/kubeconfig'
echo 'kubectl --context kind-day2 -n python-app port-forward service/daybook 8090:80'
echo 'Then browse http://localhost:8090 on the second laptop.'
