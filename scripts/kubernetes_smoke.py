"""Exercise the deployed Orders API and retain a row for the PVC restart check."""

import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request(base_url, method, path, payload=None):
    """Return status and JSON for a real HTTP request, including error responses."""
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {} if payload is None else {"Content-Type": "application/json"}
    req = Request(base_url + path, data=data, headers=headers, method=method)
    try:
        response = urlopen(req, timeout=5)  # pylint: disable=consider-using-with
    except HTTPError as error:
        response = error
    with response:
        status_code = response.code
        raw = response.read()
    if not raw:
        return status_code, None
    try:
        return status_code, json.loads(raw)
    except json.JSONDecodeError:
        return status_code, {"raw": raw.decode("utf-8", errors="replace")}


def expect(condition, message):
    """Stop the acceptance run at the first unexpected result."""
    if not condition:
        raise AssertionError(message)


def wait_for(base_url, path):
    """Allow the ingress controller and database connection to become ready."""
    last_result = None
    for _ in range(90):
        try:
            last_result = request(base_url, "GET", path)
            if last_result[0] == 200:
                return last_result[1]
        except (URLError, TimeoutError, ConnectionError) as error:
            last_result = str(error)
        time.sleep(2)
    raise RuntimeError(f"Timed out waiting for {path}: {last_result}")


def prepare(base_url, report_dir):
    """Create mixed statuses and verify filtering, actions and error responses."""
    expect(wait_for(base_url, "/health") == {"status": "OK"}, "Unexpected health JSON")
    payload = {"customer_id": 987654, "status": "NEW",
               "items": [{"product_id": 9, "quantity": 2, "unit_price": 12.50}]}
    code, original = request(base_url, "POST", "/orders", payload)
    expect(code == 201, f"Create returned {code}: {original}")
    order_id = original["id"]
    code, cancelled = request(base_url, "PUT", f"/orders/{order_id}/cancel")
    expect(code == 200 and cancelled["status"] == "CANCELLED", "Cancellation failed")
    expect(cancelled["items"] == original["items"] and cancelled["subtotal"] == 25,
           "Cancellation changed items or subtotal")
    expect(request(base_url, "PUT", f"/orders/{order_id}/cancel") == (200, cancelled),
           "Repeated cancellation changed the order")
    ids = [order_id]
    for order_status in ("NEW", "SHIPPED", "DELIVERED"):
        code, other = request(base_url, "POST", "/orders",
                              {"customer_id": 987655, "status": order_status})
        expect(code == 201, "Could not create the nonmatching control order")
        ids.append(other["id"])
        if order_status != "NEW":
            code, error = request(base_url, "PUT", f"/orders/{other['id']}/cancel")
            expect(code == 409 and error["status"] == 409, "Invalid transition was accepted")
    code, matches = request(base_url, "GET", "/orders?status=CANCELLED")
    expect(code == 200 and order_id in [row["id"] for row in matches], "Matching row missing")
    expect(all(row["status"] == "CANCELLED" for row in matches), "Status query was ignored")
    code, all_orders = request(base_url, "GET", "/orders")
    expect(code == 200 and set(ids).issubset({row["id"] for row in all_orders}),
           "Unfiltered collection did not return all control orders")
    for query in ("status=invalid", "status=", "unsupported=1", "status=NEW&status=SHIPPED"):
        code, error = request(base_url, "GET", "/orders?" + query)
        expect(code == 400 and error["status"] == 400, "Invalid query did not return JSON 400")
    code, error = request(base_url, "PUT", "/orders/0/cancel")
    expect(code == 404 and error["status"] == 404, "Missing order did not return JSON 404")
    (report_dir / "orders-state.json").write_text(
        json.dumps({"cancelled": cancelled, "ids": ids}, indent=2), encoding="utf-8")
    print("PASS: HTTP health, CRUD, mixed-status filtering, cancellation, JSON 400/404/409", flush=True)


def verify(base_url, report_dir):
    """Compare persisted order and item values after PostgreSQL Pod recreation."""
    saved = json.loads((report_dir / "orders-state.json").read_text(encoding="utf-8"))
    expected = saved["cancelled"]
    actual = wait_for(base_url, f"/orders/{expected['id']}")
    expect(actual == expected, "Order/item data changed after PostgreSQL Pod restart")
    print("PASS: persisted order and item values match the saved pre-restart snapshot", flush=True)


def cleanup(base_url, report_dir):
    """Delete only orders created by this acceptance run."""
    saved = json.loads((report_dir / "orders-state.json").read_text(encoding="utf-8"))
    for order_id in saved["ids"]:
        code, _ = request(base_url, "DELETE", f"/orders/{order_id}")
        expect(code == 204, f"Cleanup for order {order_id} returned {code}")
    print("PASS: DELETE returned 204 for the verification orders", flush=True)


if __name__ == "__main__":
    url, directory, action = sys.argv[1:]
    reports = Path(directory)
    reports.mkdir(parents=True, exist_ok=True)
    {"prepare": prepare, "verify": verify, "cleanup": cleanup}[action](url, reports)
