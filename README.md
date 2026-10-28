# NYU DevOps Orders Service

[![CI](https://github.com/CSCI-GA-2820-FA26-003/orders/actions/workflows/ci.yml/badge.svg)](https://github.com/CSCI-GA-2820-FA26-003/orders/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/CSCI-GA-2820-FA26-003/orders/branch/master/graph/badge.svg)](https://codecov.io/gh/CSCI-GA-2820-FA26-003/orders)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Language-Python-blue.svg)](https://python.org/)

A RESTful microservice for managing customer **Orders** and the **Items** that belong to them.

## Overview

The Orders service lets clients create, read, update, list, and delete Orders, and
add, read, update, list, and delete the Items within an Order. Each Order belongs to a customer
and holds a collection of Items; each Item is a single line of an Order (a product,
a quantity, and a unit price). The service is built with Flask and SQLAlchemy and
stores its data in PostgreSQL.

The `/service` folder contains the `models` package with the `Order` and `Item`
models, and `routes.py` with the REST API. The `/tests` folder contains test suites
for the models and the routes.

## Prerequisites

The development environment runs entirely inside a Docker container, so you only
need the following installed on your computer:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine on Linux)
- [Visual Studio Code](https://code.visualstudio.com/)
- The [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
  extension for VSCode

## Initial Setup

1. Clone the repository and open it in VSCode:

   ```bash
   git clone https://github.com/CSCI-GA-2820-FA26-003/orders.git
   cd orders
   code .
   ```

2. Make sure Docker is running.
3. When VSCode prompts you, click **Reopen in Container**. Otherwise open the Command
   Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) and run
   **Dev Containers: Reopen in Container**.

The first build takes a few minutes. VSCode uses `.devcontainer/docker-compose.yml`
to start two containers: `app`, where you develop and run the service, and
`postgres`, a PostgreSQL 15 database. All of the commands below are run in the
VSCode terminal inside the `app` container.

## Dependencies

You do not need to install dependencies yourself. When the dev container image is
built, the `.devcontainer/Dockerfile` runs `pipenv install --system --dev`, which
installs every package in `Pipfile.lock` (Flask, SQLAlchemy, psycopg, pytest,
coverage, flake8, pylint, and so on).

If you change the `Pipfile`, or a package is missing, install the dependencies
manually from inside the container:

```bash
make install    # runs: sudo pipenv install --system --dev
```

To pick up dependency changes for everyone, rebuild the container with
**Dev Containers: Rebuild Container**.

## Database Configuration

The service reads its database connection from the `DATABASE_URI` environment
variable. The dev container sets it in `.devcontainer/docker-compose.yml`:

```text
DATABASE_URI=postgresql+psycopg://postgres:pgs3cr3t@postgres:5432/postgres
```

| Setting  | Value                                                |
| -------- | ---------------------------------------------------- |
| Driver   | `postgresql+psycopg` (SQLAlchemy with psycopg 3)     |
| Host     | `postgres` (the database container's hostname)       |
| Port     | `5432`                                               |
| User     | `postgres`                                           |
| Password | `pgs3cr3t`                                           |
| Database | `postgres`                                           |

If `DATABASE_URI` is not set, `service/config.py` falls back to
`postgresql+psycopg://postgres:postgres@localhost:5432/postgres`. The database data
is kept in the `postgres` Docker volume, so it survives container restarts. To reach
the database from your own computer, uncomment the `ports` section of the `postgres`
service in `docker-compose.yml` and rebuild the container.

**Database initialization:** you do not need to create the tables by hand. When the
service starts, it calls `db.create_all()`, which creates any tables that do not
exist yet and leaves existing tables and data alone.

## Starting the Service

1. Open a terminal in VSCode (inside the dev container).
2. Start the service with either command:

   ```bash
   make run        # runs honcho start
   # or
   honcho start
   ```

   Honcho runs the `web` process in the `Procfile`, which starts gunicorn on
   `0.0.0.0:$PORT`. `PORT` is set to `8080` in the dev container.
3. The service is available at **<http://localhost:8080>**. Port 8080 is forwarded
   from the container, so you can open it in your browser or call it from your
   computer. Check that it is up with:

   ```bash
   curl -i http://localhost:8080/
   ```

4. Press `Ctrl+C` to stop the service.

All request and response bodies are JSON.

## Running the Tests

> **Warning:** the tests delete every Order and Item in the database they connect
> to before each test case. They use the `DATABASE_URI` environment variable, which
> in the dev container points at the development database. Running `make test`
> without changing it **will erase your development data**.

### Configure a separate test database

1. Create a `testdb` database on the `postgres` server (only needed once, since it
   is kept in the Docker volume):

   ```bash
   python -c "import psycopg; psycopg.connect('postgresql://postgres:pgs3cr3t@postgres:5432/postgres', autocommit=True).execute('CREATE DATABASE testdb')"
   ```

2. Point `DATABASE_URI` at the test database for your test runs:

   ```bash
   export DATABASE_URI=postgresql+psycopg://postgres:pgs3cr3t@postgres:5432/testdb
   ```

   This only lasts for the current terminal. Use a separate terminal for
   `make run` if you want the service to keep using the development database.

3. Run the tests and the linter:

   ```bash
   make test       # pytest with coverage (>= 95%)
   make lint       # flake8 and pylint
   ```

   You can also set the variable for a single run:
   `DATABASE_URI=postgresql+psycopg://postgres:pgs3cr3t@postgres:5432/testdb make test`.

The tables are created automatically when the tests load the app, so the empty
`testdb` database is all you need.

### Resetting the database

`flask db-create` **drops all tables and recreates them**, which deletes all of
their data. It acts on the database in `DATABASE_URI`. You do **not** need to run it
before every test run, since the tests clean up their own data. Use it only when
the tables are out of date, for example after a model change adds or renames a
column (`db.create_all()` never changes tables that already exist):

```bash
flask db-create
```

### Coverage reports

`make test` measures coverage of the `service` package and fails if total coverage
is below **95%** (`--cov-fail-under=95`). A summary with missing line numbers is
printed in the terminal.

To see exactly which lines are not covered, generate an HTML report after running
the tests:

```bash
coverage html
```

The report is written to `htmlcov/` (ignored by git). The project folder is shared
between the container and your computer, so open `htmlcov/index.html` from your
local clone in a browser (or right-click it in the VSCode Explorer and choose
**Reveal in File Explorer** / **Reveal in Finder**). Click a file to see its
uncovered lines highlighted.

## Data Model

### Order

| Field         | Type              | Notes                                                        |
| ------------- | ----------------- | ------------------------------------------------------------ |
| `id`          | integer           | Read-only, assigned by the service                           |
| `customer_id` | integer           | **Required**                                                 |
| `status`      | string            | One of `NEW`, `SHIPPED`, `DELIVERED`, `CANCELLED`; defaults to `NEW` |
| `subtotal`    | number            | Read-only, computed as the sum of the Items' `line_total`    |
| `created_at`  | ISO 8601 datetime | Read-only                                                    |
| `updated_at`  | ISO 8601 datetime | Read-only                                                    |
| `items`       | array of Item     | Optional on create                                           |

### Item

| Field        | Type    | Notes                                                       |
| ------------ | ------- | ----------------------------------------------------------- |
| `id`         | integer | Read-only, assigned by the service                          |
| `order_id`   | integer | Read-only, the Order this Item belongs to                   |
| `product_id` | integer | **Required**; must be positive for `POST /orders/{order_id}/items` |
| `quantity`   | integer | **Required**, between 1 and 999                             |
| `unit_price` | number  | **Required**, between 0 and 99999999.99, at most 2 decimals |
| `line_total` | number  | Read-only, computed as `quantity × unit_price`              |

## API Reference

### Routes summary

| Method   | URI                                     | Description                     | Success          |
| -------- | --------------------------------------- | ------------------------------- | ---------------- |
| `GET`    | `/`                                     | Service information             | `200 OK`         |
| `POST`   | `/orders`                               | Create an Order                 | `201 Created`    |
| `GET`    | `/orders`                               | List all Orders                 | `200 OK`         |
| `GET`    | `/orders/{order_id}`                    | Read an Order by id             | `200 OK`         |
| `PUT`    | `/orders/{order_id}`                    | Update an Order                 | `200 OK`         |
| `DELETE` | `/orders/{order_id}`                    | Delete an Order and its Items   | `204 No Content` |
| `POST`   | `/orders/{order_id}/items`              | Add an Item to an Order         | `201 Created`    |
| `GET`    | `/orders/{order_id}/items`              | List all Items in an Order      | `200 OK`         |
| `GET`    | `/orders/{order_id}/items/{item_id}`    | Read an Item from an Order      | `200 OK`         |
| `PUT`    | `/orders/{order_id}/items/{item_id}`    | Update an Item in an Order      | `200 OK`         |
| `DELETE` | `/orders/{order_id}/items/{item_id}`    | Delete an Item from an Order    | `204 No Content` |

### Error responses

Errors are returned as JSON with `status`, `error`, and `message` fields, for example:

```json
{"status": 404, "error": "Not Found", "message": "404 Not Found: Order with id [123] was not found"}
```

| Status                       | When                                                              |
| ---------------------------- | ----------------------------------------------------------------- |
| `400 Bad Request`            | The request body is missing fields or contains invalid data       |
| `404 Not Found`              | The Order or Item does not exist                                  |
| `405 Method Not Allowed`     | The HTTP method is not supported on the URI                       |
| `409 Conflict`               | The Order's status does not allow it to be modified               |
| `415 Unsupported Media Type` | A request body was sent without `Content-Type: application/json`  |
| `500 Internal Server Error`  | An unexpected server error occurred                               |
| `503 Service Unavailable`    | The service is temporarily unavailable                            |

For 5xx errors the `message` is a generic `"An unexpected error occurred."` (or
`"The service is temporarily unavailable."` for 503) so that internal details are
not exposed.

### Request IDs

Every response, including errors, carries an `X-Request-ID` header. If the client
sends an `X-Request-ID` header it is echoed back; otherwise the service generates a
UUID.

### Service information

```bash
curl -i http://localhost:8080/
```

`GET /` returns **200 OK** with the service name, version, and the URI of the
Orders collection:

```json
{
  "name": "Orders Service",
  "version": "1.0.0",
  "endpoints": {"orders": "/orders"}
}
```

### Create an order

```bash
curl -i -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id": 42, "items": [{"product_id": 789, "quantity": 2, "unit_price": 12.50}]}'
```

`POST /orders` creates a new Order, along with any `items` included in the body.
`status` defaults to `NEW` when omitted.

- **201 Created:** The body contains the new Order (including its `id`, computed
  `subtotal`, and Items), and the `Location` header holds the Order's URI,
  e.g. `http://localhost:8080/orders/123`.
- **400 Bad Request:** `customer_id` is missing or not an integer, `status` is not
  a valid value, or an Item is invalid.
- **415 Unsupported Media Type:** The `Content-Type` is not `application/json`.

### List all orders

```bash
curl -i http://localhost:8080/orders
```

`GET /orders` returns **200 OK** with an array of every Order, each including its
Items. Returns `[]` when there are no Orders.

### Read an order

```bash
curl -i http://localhost:8080/orders/123
```

`GET /orders/{order_id}` returns **200 OK** with the Order and all of its Items:

```json
{
  "id": 123,
  "customer_id": 42,
  "status": "NEW",
  "subtotal": 25.0,
  "created_at": "2026-10-20T14:30:00",
  "updated_at": "2026-10-20T14:30:00",
  "items": [
    {"id": 456, "order_id": 123, "product_id": 789, "quantity": 2, "unit_price": 12.5, "line_total": 25.0}
  ]
}
```

If the Order does not exist, the endpoint returns **404 Not Found**. Reading an
Order does not modify it.

### Update an order

```bash
curl -i -X PUT http://localhost:8080/orders/123 \
  -H "Content-Type: application/json" \
  -d '{"customer_id": 42, "status": "SHIPPED"}'
```

`PUT /orders/{order_id}` updates an existing Order. The body must include
`customer_id`. If `status` is omitted, the Order keeps its current status. If
`items` is included, it replaces the Order's current Items; otherwise the existing
Items are kept.

- **200 OK:** The body contains the updated Order.
- **400 Bad Request:** `customer_id` is missing or not an integer, `status` is not
  a valid value, or an Item is invalid. The Order is left unchanged.
- **404 Not Found:** The Order does not exist.
- **415 Unsupported Media Type:** The `Content-Type` is not `application/json`.

### Delete an order

```bash
curl -i -X DELETE http://localhost:8080/orders/123
```

- **204 No Content:** The Order and all associated Items are deleted in the same
  database transaction. The response body is empty. Empty Orders can also be
  deleted. Other Orders and their Items are unaffected.
- DELETE is idempotent: if the Order does not exist (for example, it was already
  deleted), the service also returns **204 No Content** and nothing is changed.

### Add an item to an order

```bash
curl -i -X POST http://localhost:8080/orders/123/items \
  -H "Content-Type: application/json" \
  -d '{"product_id": 789, "quantity": 2, "unit_price": 12.50}'
```

`POST /orders/{order_id}/items` adds an Item to the Order and recomputes the
Order's `subtotal`. The body must contain `product_id`, `quantity`, and
`unit_price`; the read-only fields `id`, `order_id`, and `line_total` must not be
sent.

- **201 Created:** The body contains the new Item, and the `Location` header holds
  the Item's URI, e.g. `http://localhost:8080/orders/123/items/456`.
- **400 Bad Request:** A field is missing or invalid, or a read-only field was sent.
- **404 Not Found:** The Order does not exist.
- **409 Conflict:** The Order's status is not `NEW`, so it can no longer be modified.
- **415 Unsupported Media Type:** The `Content-Type` is not `application/json`.

### List all items in an order

```bash
curl -i http://localhost:8080/orders/123/items
```

`GET /orders/{order_id}/items` returns **200 OK** with an array of all Items
belonging to that Order. Existing Orders with no Items return `[]`. Missing Orders
return **404 Not Found**. Listing Items does not change any data or include Items
belonging to other Orders.

### Read an item from an order

```bash
curl -i http://localhost:8080/orders/123/items/456
```

`GET /orders/{order_id}/items/{item_id}` returns **200 OK** with the Item:

```json
{"id": 456, "order_id": 123, "product_id": 789, "quantity": 2, "unit_price": 12.5, "line_total": 25.0}
```

If the Order or Item does not exist, or the Item belongs to a different Order,
the endpoint returns **404 Not Found**. Reading an Item does not modify its Order
or any Items.

### Update an item in an order

```bash
curl -i -X PUT http://localhost:8080/orders/123/items/456 \
  -H "Content-Type: application/json" \
  -d '{"quantity": 3}'
```

`PUT /orders/{order_id}/items/{item_id}` partially updates an Item. Only
`quantity` and/or `unit_price` may be sent; fields not supplied keep their current
values, and `line_total` and the Order's `subtotal` reflect the new values.

- **200 OK:** The body contains the updated Item.
- **400 Bad Request:** The body is empty or not a JSON object, contains an
  immutable field (`id`, `order_id`, `product_id`) or an unknown field, or has an
  invalid `quantity` or `unit_price`.
- **404 Not Found:** The Order or Item does not exist, or the Item belongs to a
  different Order.
- **415 Unsupported Media Type:** The `Content-Type` is not `application/json`.

### Delete an item from an order

```bash
curl -i -X DELETE http://localhost:8080/orders/123/items/456
```

- **204 No Content:** Only the specified Item belonging to this Order is deleted,
  and the response body is empty. The Order, its remaining Items, and other Orders
  are preserved. The Order's computed `subtotal` reflects the remaining Items.
  Deleting the last Item leaves an empty Order with a subtotal of zero.
- DELETE is idempotent: if the Order or Item does not exist, or the Item belongs
  to a different Order, the service also returns **204 No Content** and nothing is
  changed. Repeated deletion also returns 204.

## Contents

The project contains the following:

```text
.gitignore          - this will ignore vagrant and other metadata files
.flaskenv           - Environment variables to configure Flask
.gitattributes      - File to fix Windows CRLF issues
.devcontainer/      - Folder with support for VSCode Remote Containers
dot-env-example     - copy to .env to use environment variables
Pipfile             - Pipenv list of Python libraries required by your code

service/                     - service python package
├── __init__.py              - package initializer
├── config.py                - configuration parameters
├── routes.py                - module with service routes
├── models                   - business models package
│   ├── __init__.py          - package initializer
│   ├── persistent_base.py   - shared database persistence methods
│   ├── order.py             - Order model
│   └── item.py              - Item model
└── common                   - common code package
    ├── cli_commands.py      - Flask command to recreate all tables
    ├── error_handlers.py    - HTTP error handling code
    ├── log_handlers.py      - logging setup code
    └── status.py            - HTTP status constants

tests/                       - test cases package
├── __init__.py              - package initializer
├── factories.py             - Factory for testing with fake objects
├── test_cli_commands.py     - test suite for the CLI
├── test_error_handlers.py   - test suite for the error handlers
├── test_order.py            - test suite for the Order model
├── test_item.py             - test suite for the Item model
└── test_routes.py           - test suite for service routes
```

## License

Copyright (c) 2016, 2025 [John Rofrano](https://www.linkedin.com/in/JohnRofrano/). All rights reserved.

Licensed under the Apache License. See [LICENSE](LICENSE)

This repository is part of the New York University (NYU) masters class: **CSCI-GA.2820-003 DevOps and Agile Methodologies** created and taught by [John Rofrano](https://cs.nyu.edu/~rofrano/), Adjunct Instructor, NYU Courant Institute, Graduate Division, Computer Science, and NYU Stern School of Business.

## Sprint 2 API additions

`GET /orders?status=NEW` filters at the model query level. Supported statuses use
existing enum names: `NEW`, `SHIPPED`, `DELIVERED`, and `CANCELLED`. Without a query,
all orders are returned; a valid filter with no matches returns HTTP 200 and `[]`.
An empty, unknown or incorrectly cased status, repeated `status` parameters, or an
unsupported query key returns HTTP 400 using the existing JSON error envelope.

`GET /health` returns HTTP 200 with `{"status":"OK"}` for liveness checks.

`PUT /orders/{order_id}/cancel` changes a `NEW` order to `CANCELLED` and returns
HTTP 200 with the order JSON. It preserves the order and its items. Repeating the
request returns 200 with the same cancelled order. Cancelling a `SHIPPED` or
`DELIVERED` order returns 409; a missing order returns 404. Both errors use the
existing `status`, `error`, `message` envelope.

```bash
curl -i http://localhost:8080/health
curl -i -X PUT http://localhost:8080/orders/1/cancel
```

## Continuous integration

`.github/workflows/ci.yml` runs unit tests against a dedicated PostgreSQL `testdb`,
flake8 and pylint on pull requests targeting `master` and pushes to `master`.
Tests enforce at least 95% service coverage and produce `coverage.xml`. Codecov
uploads use the existing `CODECOV_TOKEN` repository secret and fail if an upload
fails. Fork PRs still run all quality checks; the upload is skipped because
GitHub does not expose repository secrets to them.

## Local Kubernetes

Run these commands from a Linux shell or the development container with Docker,
k3d, kubectl, make and Python 3 installed. Docker must be running. The local
registry is exposed at `localhost:5000`; Kubernetes maps this registry to
`k3d-cluster-registry:5000` using `config/registries.yaml`.

```bash
make cluster
make build
make push
make deploy
curl -fsS http://localhost:8080/health
```

The cluster is named `nyu-devops`, the namespace is `orders`, and ingress listens
on `127.0.0.1:8080`. PostgreSQL runs as a StatefulSet with database `orders` and a
1 GiB PVC using K3s `local-path` storage. Deployment creates a random local
password in Secret `orders-db` once, then reuses it on subsequent deployments.
The Orders application reads its `DATABASE_URI` from the same Secret. No database
password is committed to the manifests. `make deploy` selects the context
`k3d-nyu-devops` explicitly and waits for PostgreSQL before starting Orders.

Demonstrate the API and persistence in this local cluster:

```bash
curl -i -X POST http://localhost:8080/orders \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":123,"status":"NEW","items":[{"product_id":9,"quantity":2,"unit_price":12.50}]}'
# Substitute the ID returned by POST below.
curl -i http://localhost:8080/orders/1
curl -i http://localhost:8080/orders
curl -i -X PUT http://localhost:8080/orders/1/cancel
kubectl --context k3d-nyu-devops -n orders exec postgres-0 -- pg_isready -U postgres -d orders
kubectl --context k3d-nyu-devops -n orders rollout restart statefulset/postgres
kubectl --context k3d-nyu-devops -n orders rollout status statefulset/postgres --timeout=180s
curl -i http://localhost:8080/orders/1
curl -i -X DELETE http://localhost:8080/orders/1
```

The PVC survives a PostgreSQL pod restart. Removing the whole k3d cluster removes
its node-local storage. Use `make cluster-rm` only when the cluster is disposable.
These commands are the acceptance procedure; local Kubernetes and Codecov results
must be observed before their stories are marked complete.

For automated acceptance checks from Windows with the existing `nyu-project`
development container, run from the project root in a normal PowerShell session with Docker access:

```powershell
powershell -NoProfile -File ".\scripts\verify-kubernetes.ps1"
```

This first runs the PostgreSQL tests, lint, image and HTTP verification. It then
copies the current deployment inputs into an isolated snapshot in the existing
Linux development container using checksum-verified exec stdin transfer, then runs
the actual `make cluster`, `make build`,
`make push` and `make deploy` targets. The cluster, registry and ports are unique
to the run. The checks cover ingress/API behavior with mixed statuses, database
connectivity, recreation of the PostgreSQL Pod with the same PVC/PV, persisted
order/item values, and repeated deployment without replacing the database Secret.
Use `-SkipPostgres` only when repeating the Kubernetes stage after the tests pass.
Use `-Container NAME` if the existing development container has a different name.

Reports are copied to `.test-tmp/kubernetes-<run-id>/`. The verification cluster
remains inside the development container for inspection; `connection.txt` records
the commands to inspect it. Its ingress endpoint is inside that container.
Access from a Windows browser requires forwarding that port through VS Code.
The runner does not verify GitHub Actions or Codecov. Both verification scripts
stop on failure; consult `SPRINT2.md` for checks actually observed so far.

The Makefile also accepts `REGISTRY_NAME`, `REGISTRY_PORT`, `REGISTRY_CONFIG` and
`INGRESS_PORT` overrides. A custom registry name/port requires a matching mirror
configuration; the automated runner generates it for its isolated cluster.
To resume a retained verification cluster, pass `-SkipPostgres -ResumeRun RUN_ID`,
where `RUN_ID` is the 12-character suffix of the original report directory.
The launcher validates that run's metadata and unchanged image inputs before
reusing its image and cluster. Recovery repairs aliases only on that run's local
registry network and restarts the pending Orders rollout; existing database/PVC
and registry data are preserved. Fresh clusters use an explicit registry name
that exactly matches their mirror configuration.

To publish this Sprint 2 feature branch from normal Windows PowerShell after local
verification, run from the repository root:

```powershell
powershell -NoProfile -File ".\scripts\publish-sprint2.ps1" -VerifyFreshCluster
```

The launcher checks that the branch is clean, completes GitHub CLI login in the
user's terminal/browser when needed, verifies a fresh isolated K3s cluster,
pushes the feature branch and creates a draft PR. It uses the GitHub CLI identity
for that push without changing global Git credential configuration. Publication
results are saved under `.test-tmp/github-handoff-<run-id>/`; actual CI and Codecov
reports must then be reviewed on the PR. Omit `-VerifyFreshCluster` when retrying
publication after the fresh cluster check has already passed.

CI also runs a fresh K3s acceptance job after tests and lint. It verifies the
actual Makefile build/push/deploy targets, Ingress API and PostgreSQL Pod/PVC
persistence, then saves allowlisted reports as the `kubernetes-acceptance`
workflow artifact. Kubeconfig and database Secret values are excluded.
