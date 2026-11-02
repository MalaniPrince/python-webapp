#!/usr/bin/env bash
set -euo pipefail
: "${GITHUB_SHA:?Missing release commit}"
[[ "$GITHUB_SHA" =~ ^[a-f0-9]{40}$ ]] || exit 2
archive=${1:?Usage: deploy-day2.sh IMAGE_ARCHIVE}
image="python-webapp:sha-${GITHUB_SHA}"
kube=(kubectl --context kind-day2 --namespace python-app)
"${kube[@]}" get deployment daybook >/dev/null
"${kube[@]}" get pvc daybook-data >/dev/null
sudo -n /usr/local/sbin/daybook-load-image "$image" "$archive"
release_dir=$(mktemp -d)
trap 'rm -rf -- "$release_dir"' EXIT
cp k8s.yaml "$release_dir/k8s.yaml"
cat > "$release_dir/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - k8s.yaml
images:
  - name: python-webapp
    newTag: sha-${GITHUB_SHA}
EOF
# Keep the existing database PVC; only the deployment's image tag changes.
kubectl --context kind-day2 apply -k "$release_dir"
if ! "${kube[@]}" rollout status deployment/daybook --timeout=300s; then
  "${kube[@]}" get pods -o wide || true
  "${kube[@]}" describe deployment daybook || true
  "${kube[@]}" logs deployment/daybook --tail=80 || true
  echo 'Rollout failed; restoring the previous deployment revision.' >&2
  "${kube[@]}" rollout undo deployment/daybook
  "${kube[@]}" rollout status deployment/daybook --timeout=300s
  exit 1
fi
"${kube[@]}" get pods,pvc,services
deployed_image=$("${kube[@]}" get deployment daybook -o jsonpath='{.spec.template.spec.containers[?(@.name=="web")].image}')
[[ "$deployed_image" == "$image" ]]
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  printf '### Deployed to kind-day2\n\nCommit: `%s`\n\nImage: `%s`\n\nDeployment: `python-app/daybook`\n' "$GITHUB_SHA" "$image" >> "$GITHUB_STEP_SUMMARY"
fi
