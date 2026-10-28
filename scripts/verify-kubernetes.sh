#!/usr/bin/env bash
# Run inside the configured Linux development container with its Docker daemon.
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
report_dir="$PWD/.test-tmp/kubernetes"
mkdir -p "$report_dir"
exec > >(tee "$report_dir/verification.log") 2>&1
cluster="orders-s2-$(python3 -c 'import secrets; print(secrets.token_hex(5))')"
registry_name="k3d-${cluster}-registry"
export KUBECONFIG="$PWD/.verification-kubeconfig"
if [[ -f .resume.json ]]; then
    read -r cluster registry_name registry_port ingress_port source_root < <(python3 - <<'PY'
import json, re
from pathlib import Path
state = json.loads(Path('.resume.json').read_text())
cluster = state['cluster']
registry = state['registry_name']
source = state['source_root']
assert re.fullmatch(r'orders-s2-[a-f0-9]{10}', cluster)
assert registry in (cluster + '-registry', 'k3d-' + cluster + '-registry')
assert re.fullmatch(r'/home/vscode/\.cache/orders-sprint2-[a-f0-9]{12}', source)
assert all(1 <= int(state[key]) <= 65535 for key in ('registry_port', 'ingress_port'))
old = Path(source)
current = Path.cwd()
# Reuse the built image only if all image inputs are still byte-for-byte equal.
names = ['Dockerfile', 'Pipfile', 'Pipfile.lock', 'wsgi.py']
old_service = {p.relative_to(old).as_posix() for p in (old / 'service').rglob('*')
               if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
new_service = {p.relative_to(current).as_posix() for p in (current / 'service').rglob('*')
               if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
assert old_service == new_service, 'Image inputs changed; use a fresh run'
assert all((old / name).read_bytes() == (current / name).read_bytes()
           for name in names + sorted(old_service)), 'Image inputs changed; use a fresh run'
print(cluster, registry, state['registry_port'], state['ingress_port'], source)
PY
)
    export KUBECONFIG="$source_root/.verification-kubeconfig"
    [[ -f "$KUBECONFIG" ]] || { printf 'Prior private kubeconfig is missing\n'; exit 1; }
fi
context="k3d-${cluster}"
kube=(kubectl --context "$context" --namespace orders)
completed=0
finish() {
    result=$?
    set +e
    if [[ "$completed" == 1 && "$result" == 0 ]]; then
        printf 'Result: PASSED\n'
    else
        printf 'Result: FAILED (exit %s)\n' "$result"
        kubectl --context "$context" --request-timeout=10s -n orders get pods,svc,ingress,pvc -o wide
        kubectl --context "$context" --request-timeout=10s -n orders get events --sort-by=.metadata.creationTimestamp | tail -50
        kubectl --context "$context" --request-timeout=10s -n orders logs deployment/orders --tail=100
        kubectl --context "$context" --request-timeout=10s -n orders logs postgres-0 --tail=100
    fi
    printf 'Verification cluster (retained if creation succeeded): %s\n' "$cluster"
    printf 'Kubeconfig: %s\n' "$KUBECONFIG"
    printf 'Reports: %s\n' "$report_dir"
    printf 'Use k3d cluster delete %s only when this verification cluster is disposable.\n' "$cluster"
}
trap finish EXIT
for tool in docker make k3d kubectl python3; do
    command -v "$tool" >/dev/null || { printf 'Missing development tool: %s\n' "$tool"; exit 1; }
done
# The existing development container may have just started its nested daemon.
engine_ready=0
for ((attempt=0; attempt<30; attempt++)); do
    if docker info >/dev/null 2>&1; then engine_ready=1; break; fi
    sleep 1
done
[[ "$engine_ready" == 1 ]] || { printf 'Development-container Docker daemon is unavailable\n'; exit 1; }
printf 'Docker Engine: '
docker info --format '{{.ServerVersion}}'
k3d version
kubectl version --client
make --version | head -1
# Keep existing clusters, registries, ports and kubeconfig untouched.
if [[ ! -f .resume.json ]]; then
read -r registry_port ingress_port < <(python3 - <<'PY'
import socket
with socket.socket() as first, socket.socket() as second:
    first.bind(("127.0.0.1", 0))
    second.bind(("127.0.0.1", 0))
    print(first.getsockname()[1], second.getsockname()[1])
PY
)
fi
registry_config="$report_dir/registries.yaml"
cat > "$registry_config" <<EOF
mirrors:
  "localhost:${registry_port}":
    endpoint:
      - "http://${registry_name}:5000"
EOF
image="localhost:${registry_port}/orders:sprint2"
base_url="http://127.0.0.1:${ingress_port}"
make_args=("CLUSTER=$cluster" "REGISTRY_NAME=$registry_name" "REGISTRY_PORT=$registry_port"
           "REGISTRY_CONFIG=$registry_config" "INGRESS_PORT=$ingress_port" "IMAGE=$image")
if [[ -f .resume.json ]]; then
    printf 'Resuming the existing verification cluster: %s\n' "$cluster"
    docker image inspect "$image" >/dev/null
    docker container inspect "$registry_name" >/dev/null
    network="k3d-${cluster}"
    docker network inspect "$network" >/dev/null
    # Preserve the registry's image data; repair only its aliases on this owned network.
    if docker inspect --format '{{json .NetworkSettings.Networks}}' "$registry_name" | \
       python3 -c 'import json,sys; sys.exit(0 if sys.argv[1] in json.load(sys.stdin) else 1)' "$network"; then
        docker network disconnect "$network" "$registry_name"
    fi
    docker network connect --alias "$registry_name" --alias "k3d-${registry_name}" "$network" "$registry_name"
    # Start a fresh pull attempt instead of waiting through ImagePullBackOff.
    "${kube[@]}" rollout restart deployment/orders
else
    printf 'Creating an isolated K3s cluster: %s\n' "$cluster"
    make "${make_args[@]}" cluster
    make "${make_args[@]}" build
    make "${make_args[@]}" push
fi
kubectl --context "$context" wait --for=condition=Ready nodes --all --timeout=180s
make "${make_args[@]}" deploy
actual_image=$("${kube[@]}" get deployment orders -o jsonpath='{.spec.template.spec.containers[0].image}')
[[ "$actual_image" == "$image" ]] || { printf 'Deployment ignored IMAGE override\n'; exit 1; }
"${kube[@]}" exec postgres-0 -- pg_isready -U postgres -d orders
python3 scripts/kubernetes_smoke.py "$base_url" "$report_dir" prepare
old_pod=$("${kube[@]}" get pod postgres-0 -o jsonpath='{.metadata.uid}')
old_pvc=$("${kube[@]}" get pvc data-postgres-0 -o jsonpath='{.metadata.uid}')
old_pv=$("${kube[@]}" get pvc data-postgres-0 -o jsonpath='{.spec.volumeName}')
printf 'Restarting the PostgreSQL StatefulSet...\n'
"${kube[@]}" rollout restart statefulset/postgres
"${kube[@]}" rollout status statefulset/postgres --timeout=180s
new_pod=$("${kube[@]}" get pod postgres-0 -o jsonpath='{.metadata.uid}')
new_pvc=$("${kube[@]}" get pvc data-postgres-0 -o jsonpath='{.metadata.uid}')
new_pv=$("${kube[@]}" get pvc data-postgres-0 -o jsonpath='{.spec.volumeName}')
[[ "$old_pod" != "$new_pod" && "$old_pvc" == "$new_pvc" && "$old_pv" == "$new_pv" && -n "$old_pv" ]] || {
    printf 'Pod recreation/PVC identity check failed\n'; exit 1;
}
"${kube[@]}" exec postgres-0 -- pg_isready -U postgres -d orders
python3 scripts/kubernetes_smoke.py "$base_url" "$report_dir" verify
# Re-deploying must reuse the database Secret and retain the existing rows.
secret_uid=$("${kube[@]}" get secret orders-db -o jsonpath='{.metadata.uid}')
make "${make_args[@]}" deploy
[[ "$secret_uid" == "$("${kube[@]}" get secret orders-db -o jsonpath='{.metadata.uid}')" ]]
python3 scripts/kubernetes_smoke.py "$base_url" "$report_dir" verify
python3 scripts/kubernetes_smoke.py "$base_url" "$report_dir" cleanup
"${kube[@]}" get pods,svc,ingress,pvc -o wide > "$report_dir/resources.txt"
"${kube[@]}" get deployment orders -o jsonpath='{.status.availableReplicas}' > "$report_dir/available-replicas.txt"
printf 'PASS: make cluster/build/push/deploy, ingress API, PostgreSQL connectivity and Pod/PVC persistence\n'
printf 'Ingress inside the development container: %s/health\n' "$base_url"
printf 'KUBECONFIG=%q kubectl --context %q -n orders get pods\n' "$KUBECONFIG" "$context" > "$report_dir/connection.txt"
completed=1
