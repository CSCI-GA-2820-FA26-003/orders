#!/usr/bin/env bash
# Verify the local deployment through ingress and the database itself.
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8080}
read -r -a kubectl_command <<< "${KUBECTL:-kubectl --context k3d-nyu-devops --namespace default}"
response_file=$(mktemp)
order_id=

cleanup() {
    if [[ -n "$order_id" ]]; then
        curl --silent --show-error --fail --max-time 10 --request DELETE \
            "$BASE_URL/orders/$order_id" > /dev/null || true
    fi
    rm -f "$response_file"
}
trap cleanup EXIT

echo "Checking GET /health through ingress..."
status_code=$(curl --silent --show-error --fail --retry 30 --retry-delay 2 \
    --retry-connrefused --retry-all-errors --max-time 10 \
    --output "$response_file" --write-out '%{http_code}' "$BASE_URL/health")
[[ "$status_code" == "200" ]]
jq --exit-status '. == {"status": "OK"}' "$response_file"

echo "Creating an order through ingress..."
status_code=$(curl --silent --show-error --max-time 30 \
    --output "$response_file" --write-out '%{http_code}' \
    --header 'Content-Type: application/json' \
    --data '{"customer_id":2820,"items":[{"product_id":60,"quantity":2,"unit_price":12.50}]}' \
    "$BASE_URL/orders")
[[ "$status_code" == "201" ]] || { cat "$response_file"; exit 1; }
order_id=$(jq --exit-status '.id | select(type == "number" and . > 0 and . == floor)' "$response_file")
jq --exit-status '.customer_id == 2820 and .status == "NEW" and .subtotal == 25 and (.items | length) == 1' "$response_file"

echo "Checking the order was saved in PostgreSQL..."
saved_order=$("${kubectl_command[@]}" exec postgres-0 -- \
    psql --username=postgres --dbname=orders --tuples-only --no-align \
    --command="SELECT count(*) FROM \"order\" WHERE id = $order_id AND customer_id = 2820;")
[[ "$saved_order" == "1" ]]
saved_item=$("${kubectl_command[@]}" exec postgres-0 -- \
    psql --username=postgres --dbname=orders --tuples-only --no-align \
    --command="SELECT count(*) FROM item WHERE order_id = $order_id AND product_id = 60 AND quantity = 2 AND unit_price = 12.50;")
[[ "$saved_item" == "1" ]]

curl --silent --show-error --fail --max-time 10 "$BASE_URL/orders/$order_id" \
    | jq --exit-status --argjson id "$order_id" '.id == $id and .customer_id == 2820 and .subtotal == 25'
echo "Ingress health, order creation, and PostgreSQL persistence passed."
