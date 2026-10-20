# NYU DevOps Orders Service

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

## Running the Service

With the service running in the development container via `honcho start`, the API
is available at `http://localhost:8080`. All request and response bodies are JSON.

## Running the Tests
       flask db-create   # recreate the tables
       make test         # pytest with coverage (>= 95%)
       make lint         # flake8 and pylint

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
- **404 Not Found:** The Order or Item does not exist, or the Item belongs to a
  different Order. Repeated deletion also returns 404.

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

This repository is part of the New York University (NYU) masters class: **CSCI-GA.2820-001 DevOps and Agile Methodologies** created and taught by [John Rofrano](https://cs.nyu.edu/~rofrano/), Adjunct Instructor, NYU Courant Institute, Graduate Division, Computer Science, and NYU Stern School of Business.
