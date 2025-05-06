# Delivery Hours Service

Your task is to implement the Delivery Hours Service!

This README.md describes the development setup for the Delivery Hours Service as well as what we expect from you.
[SYSTEM_SPECIFICATION.md](./SYSTEM_SPECIFICATION.md) contains detailed specifications of our Delivery Hours Service and its dependencies.

To make this assignment as realistic as possible, we have made some technology choices which align with what we commonly use in our Python backend projects at Wolt.
You'll be using FastAPI as a web framework, pytest for testing, Ruff for formatting and linting, mypy for static type checking, and Poetry for managing dependencies.
There's some boilerplate code to get you up and running.
Additionally, there's a Docker Compose setup and a Makefile included for convenient development.

It's perfectly ok if you don't have previous experience with all the used technologies.
The provided boilerplate code will get you up and running quickly anyway.
For example, previous experience with FastAPI is not expected.
If some of technologies used in this project are new to you, please mention them in the _Notes from the applicant_ section in this README.

## Your task
**Implement the _GET /delivery-hours_ endpoint and tests for it. See the specification in [SYSTEM_SPECIFICATION.md](./SYSTEM_SPECIFICATION.md)**

There's already a placeholder for the endpoint in the provided code. Additionally, there's an example test case which should pass once you have implemented the endpoint.

### How to do it in practice
1. Clone this repository
2. Checkout a new branch `git checkout -b my-implementation`
3. Implement your solution and push the changes to your branch
4. Once you're done
   1. Open a PR (pull request). Feel free to add comments in the PR.
   2. Inform the recruiter that you've finished the assignment

### Expectations
We expect you to:
* Follow the specification described in the [SYSTEM_SPECIFICATION.md](./SYSTEM_SPECIFICATION.md).
* Adjust the code inside _delivery_hours_service_ and _tests_ as you see fit.
* Have a reasonable architecture for the Delivery Hours Service. Feel free to restructure and refactor the existing code as much as you want. Feel free to introduce new modules and packages.
* Implement pytest tests for your solution.
* Consider that this could be a real world project so the code quality should be on the level that you'd be happy to contribute in our real projects.
* Use your judgement in case you discover an edge case which is not documented in the [SYSTEM_SPECIFICATION.md](./SYSTEM_SPECIFICATION.md). In such cases, please document your choices / assumptions here in the README or in the pull request.

We **do not** expect you to:
* Adjust the ci.yml, Dockerfile, compose.yml, pre-commit.yaml, Makefile, or external-services-mock/stub.json. However, if you feel it's necessary to do changes in those, please document the reasoning for the changes in the README or in the pull request.
* Adjust the service's endpoint path, query parameters or output schema.
* Introduce authentication.
* Introduce monitoring.
* Introduce any persistence (database).
* Deploy your solution.

## Development (Docker only)
Prerequisites:
* Docker Compose V2 (aka `docker compose` without the `-` in between)
* Make

### Essentials
Get everything up and running:
```
make start
```
This starts the Docker containers for our Delivery Hours Service and a [WireMock](https://wiremock.org/) container which acts as a mock for Venue Service and Courier Service.
The _delivery_hours_service_ and _tests_ directories are volume mapped to the `delivery-hours-service` container, and it has a hot reload, so you can keep things running while doing development.
You can also access Delivery Hours Service from localhost via port 8000 and the external services via port 8080.

Bring everything down:
```
make stop
```

For convenience, there's also `make restart` which runs `stop` and `start`.

### Testing
You can run the pytest test suite with:
```
make test
```

It doesn't matter whether you have the containers already running (i.e. if you have `make start` running in another shell window) or not, `make test` works either way.

### Linting
We are using `ruff` for linting, `ruff format` for automatic code formatting, and `mypy` for static type checking.
You can run all of them with:
```
make lint
```

### Python dependencies
To add or remove dependencies, modify _pyproject.toml_ and generate a fresh lock file with:
```
make update-dependencies
```
After doing changes related to the dependencies, remember to restart (it rebuilds as well) containers with `make restart` (or `make stop` + `make start`).

## Development (local Python environment for Delivery Hours Service)
If you are happy with the Docker only development setup, you can skip this section.
However, if you prefer local development experience, follow these instructions.

Prerequisites:
* Docker Compose V2 (aka `docker compose` without the `-` in between)
* Make
* Python 3.12
* Poetry 1.5.1

### Essentials

#### Creating the local Python environment
Create a poetry environment and install the dependencies:
```
poetry install
```

Activate the virtual environment (after this you won't need to type `poetry run ...`):
```
poetry shell
```

#### Running the service

You can start the Docker dependencies (WireMock container for Venue Service and Courier Service) with:
```
make start-dependencies
```

Run the Delivery Hours Service locally with hot reload enabled:
```
uvicorn delivery_hours_service.main:app --reload
```

### Testing
```
pytest
```

### Python dependencies
To add or remove dependencies, modify _pyproject.toml_ and get the latest versions of the dependencies and a fresh _poetry.lock_ with:
```
poetry update
```

### Linting with pre-commit
We are using `ruff` for linting, `ruff format` for automatic code formatting, and `mypy` for static type checking.
For convenience, we have bundled them into a pre-commit configuration.
If you want to have pre-commit to automatically run on each commit:
```
pre-commit install
```

Or if you just want to run it over the whole codebase at times:
```
pre-commit run --all-files
```

## URLs
The urls that are accessible from localhost:
* Delivery Hours Service (our own service): http://localhost:8000 (e.g. http://localhost:8000/delivery-hours?city_slug=helsinki&venue_id=123)
* OpenAPI docs of Delivery Hours Service: http://localhost:8000/docs
* Courier Service (mocked): http://localhost:8080/courier-service (e.g. http://localhost:8080/courier-service/delivery-hours?city=helsinki)
  * Note that the mock is only configured for _helsinki_, the response is 404 for other cities
* Venue Service (mocked): http://localhost:8080/venue-service (e.g. http://localhost:8080/venue-service/venues/123/opening-hours)
   * Note that the mock is only configured for _123_, the response is 404 for other venue ids

These work both in "Docker only" and "local Python environment for Delivery Hours Service" development setups.

## Continuous integration aka CI

There's a GitHub workflow (ci.yml) which runs pre-commit (`ruff`, `ruff format`, and `mypy`) for the whole codebase and the pytest test suite on each push.
Make sure your implementation passes the CI before submitting your solution.

## Notes from the applicant

I implemented the Delivery Hours Service using a hexagonal architecture pattern that establish a clear boundary between the domain core and external dependencies.
My implementation handles complex scenarios like overnight delivery periods and minimum delivery duration requirements. I focused on building a resilient system that accurately calculates delivery hours by combining venue opening hours with courier service delivery windows.

Key features I implemented include:

- Circuit breaker pattern for resilient external service communication
- Comprehensive error handling with appropriate status codes
- Parallel processing of external service requests for improved performance
- Extensive unit and integration test coverage

I identified several areas for improvement in a production environment, particularly around API design and inter-service communication. The current use of 404 status codes in venue and courier service for "not found" scenarios leaks implementation details and creates ambiguity between client errors and valid business outcomes.

For detailed explanation of my architectural decisions, trade-offs, and improvement proposals, please see the [detailed architecture document](./delivery_hours_service/architecture.md).
