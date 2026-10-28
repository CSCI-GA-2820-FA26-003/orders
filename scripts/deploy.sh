#!/usr/bin/env bash
set -euo pipefail
cluster="${1:-nyu-devops}"
image="${2:-localhost:5000/orders:1.0}"
base_url="${3:-http://localhost:8080}"
context="k3d-${cluster}"
kube=(kubectl --context "$context" --namespace orders)

kubectl --context "$context" get nodes >/dev/null
kubectl --context "$context" apply -f k8s/namespace.yaml
if ! "${kube[@]}" get secret orders-db >/dev/null 2>&1; then
    # Hex characters are safe in both a PostgreSQL password and its connection URI.
    password=$(python3 -c 'import secrets; print(secrets.token_hex(24))')
    "${kube[@]}" create secret generic orders-db \
        --from-literal=POSTGRES_PASSWORD="$password" \
        --from-literal=DATABASE_URI="postgresql+psycopg://postgres:${password}@postgres:5432/orders"
    unset password
fi
"${kube[@]}" apply -f k8s/postgres/
"${kube[@]}" rollout status statefulset/postgres --timeout=180s
# Apply the selected image before creating Pods, including IMAGE/IMAGE_TAG overrides.
kubectl set image --local -f k8s/deployment.yaml "orders=${image}" -o yaml | "${kube[@]}" apply -f -
"${kube[@]}" apply -f k8s/service.yaml -f k8s/ingress.yaml
"${kube[@]}" rollout status deployment/orders --timeout=180s
printf 'Orders is available at %s/health\n' "$base_url"
