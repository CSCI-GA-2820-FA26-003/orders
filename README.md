# NYU DevOps Project Template

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Language-Python-blue.svg)](https://python.org/)

This is a skeleton you can use to start your projects.

**Note:** _Feel free to overwrite this `README.md` file with the one that describes your project._

## Overview

This project template contains starter code for your class project. The `/service` folder contains your `models.py` file for your model and a `routes.py` file for your service. The `/tests` folder has test case starter code for testing the model and the service separately. All you need to do is add your functionality. You can use the [lab-flask-tdd](https://github.com/nyu-devops/lab-flask-tdd) for code examples to copy from.

## Automatic Setup

The best way to use this repo is to start your own repo using it as a git template. To do this just press the green **Use this template** button in GitHub and this will become the source for your repository.

## Manual Setup

You can also clone this repository and then copy and paste the starter code into your project repo folder on your local computer. Be careful not to copy over your own `README.md` file so be selective in what you copy.

There are 4 hidden files that you will need to copy manually if you use the Mac Finder or Windows Explorer to copy files from this folder into your repo folder.

These should be copied using a bash shell as follows:

```bash
    cp .gitignore  ../<your_repo_folder>/
    cp .flaskenv ../<your_repo_folder>/
    cp .gitattributes ../<your_repo_folder>/
```

## Contents

The project contains the following:

```text
.gitignore          - this will ignore vagrant and other metadata files
.flaskenv           - Environment variables to configure Flask
.gitattributes      - File to gix Windows CRLF issues
.devcontainers/     - Folder with support for VSCode Remote Containers
dot-env-example     - copy to .env to use environment variables
pyproject.toml      - Poetry list of Python libraries required by your code

service/                   - service python package
├── __init__.py            - package initializer
├── config.py              - configuration parameters
├── models.py              - module with business models
├── routes.py              - module with service routes
└── common                 - common code package
    ├── cli_commands.py    - Flask command to recreate all tables
    ├── error_handlers.py  - HTTP error handling code
    ├── log_handlers.py    - logging setup code
    └── status.py          - HTTP status constants

tests/                     - test cases package
├── __init__.py            - package initializer
├── factories.py           - Factory for testing with fake objects
├── test_cli_commands.py   - test suite for the CLI
├── test_models.py         - test suite for business models
└── test_routes.py         - test suite for service routes
```

## Service information

With the service running in the development container via `honcho start`, request
the root endpoint to discover the service and Orders collection:

```bash
curl -i http://localhost:8080/
```

`GET /` returns **200 OK** with `Content-Type: application/json`:

```json
{
  "name": "Orders Service",
  "version": "1.0.0",
  "endpoints": {"orders": "/orders"}
}
```

## Delete an order

With the service running via `honcho start` in the development container, delete
an order by its ID:

```bash
curl -i -X DELETE http://localhost:8080/orders/123
```

- **204 No Content:** The order and all associated Items are deleted in the same
  database transaction. The response body is empty. Empty orders can also be
  deleted. Other orders and their Items are unaffected.
- **404 Not Found:** The ID does not exist, including a second deletion of the
  same order. The JSON error follows the service's `status`, `error`, and
  `message` format, for example:

  ```json
  {"status": 404, "error": "Not Found", "message": "404 Not Found: Order with id [123] was not found"}
  ```

This follows Issue #2's explicit 404 requirement for a missing order. REST
lecture slides 42 and 44 suggest 204 for missing or repeated deletions; the
current Story takes precedence.

## Delete an item from an order

```bash
curl -i -X DELETE http://localhost:8080/orders/123/items/456
```

- **204 No Content:** Only the specified Item belonging to this order is deleted,
  and the response body is empty. The order, its remaining Items, and other orders
  are preserved. The order's computed `subtotal` reflects the remaining Items.
  Deleting the last Item leaves an empty order with a subtotal of zero.
- **404 Not Found:** The order or Item does not exist, or the Item belongs to a
  different order. Repeated deletion also returns 404. Errors use the common JSON
  `status`, `error`, and `message` format.

## License

Copyright (c) 2016, 2025 [John Rofrano](https://www.linkedin.com/in/JohnRofrano/). All rights reserved.

Licensed under the Apache License. See [LICENSE](LICENSE)

This repository is part of the New York University (NYU) masters class: **CSCI-GA.2820-001 DevOps and Agile Methodologies** created and taught by [John Rofrano](https://cs.nyu.edu/~rofrano/), Adjunct Instructor, NYU Courant Institute, Graduate Division, Computer Science, and NYU Stern School of Business.
