# Delivery Window Service

![CI](https://img.shields.io/badge/CI-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen)
![Python](https://img.shields.io/badge/python-3.12-blue)

A microservice that calculates delivery time windows by combining venue opening hours and courier delivery availability.

## Overview

The Delivery Window Service calculates when deliveries are possible by finding the intersection between venue opening hours and courier availability. It provides a clean REST API for clients to query delivery windows.

## Key Features

- Calculates delivery windows by combining venue opening times and courier availability
- Handles complex time scenarios including overnight windows (crossing midnight)
- Implements robust error handling with graceful degradation
- Uses circuit breakers to prevent cascading failures
- Provides clear, consistent API responses for clients

## Architecture

This service is implemented using hexagonal architecture with four main layers:

- **Domain Layer**: Pure business entities and logic (`Time`, `TimeRange`, `DeliveryWindow`)
- **Application Layer**: Orchestration logic through use cases
- **Infrastructure Layer**: External system interactions through adapters
- **Interface Layer**: REST API endpoints and response formatting

When a request is received, the service makes concurrent API calls to Venue and Courier services, calculates the intersection of their hours, and returns the formatted delivery windows.

## Technical Decisions

### Why Hexagonal Architecture?

I chose hexagonal architecture to keep the business logic clean and testable. The core delivery window calculation doesn't need to know whether data comes from HTTP APIs, databases, or mock services. This made testing much easier, especially when dealing with complex time intersections and edge cases like overnight delivery windows.

### Circuit Breakers

External services fail. When the venue service is down, I don't want the whole delivery calculation to hang or crash. The circuit breaker pattern (using tenacity) provides graceful degradation. If one service fails, we can still return partial results or meaningful error messages.

### Concurrent API Calls

Since venue and courier services are independent, there's no reason to call them sequentially. Using asyncio.gather() cuts typical response time in half (from ~400ms to ~200ms). This matters when processing delivery windows for multiple venues.

## Business Rules

The delivery hours of a venue are calculated by finding the intersection between the venue's opening hours and courier service delivery hours. A key business rule is that delivery periods must be at least 30 minutes long.

Examples of how delivery hours are calculated:

| Venue opening hours   | Delivery hours from Courier Service | Delivery hours of venue  |
|-----------------------|--------------------------------------|---------------------------|
| 13-20                 | 14-21                                | 14-20                    |
| 13:30-15, 16-01       | 09-14, 17-00:30                      | 13:30-14, 17-00:30       |
| 13-15                 | 09-13                                | Closed                   |
| 13-15                 | 14:31-16                             | Closed (less than 30 mins)|
| Anything              | Closed                               | Closed                   |
| Closed                | Anything                             | Closed                   |

## API Documentation

### Delivery Hours Endpoint

```
GET /delivery-hours?city_slug={city_slug}&venue_id={venue_id}
```

#### Parameters

- `city_slug`: City identifier used to retrieve courier availability in that area
- `venue_id`: Unique identifier of the venue to get opening hours for

#### Response

```json
{
  "delivery_hours": {
    "Monday": "09-12, 13:30-22",
    "Tuesday": "16:45-02",
    "Wednesday": "Closed",
    "Thursday": "Closed",
    "Friday": "Closed",
    "Saturday": "Closed",
    "Sunday": "Closed"
  }
}
```

Interactive API documentation is available via:

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Running the Project

### Prerequisites

- Python 3.12+
- Docker and Docker Compose (for containerized execution)

### Local Development

1. Clone the repository

```bash
git clone https://github.com/benidevo/delivery-window-service.git
cd delivery-window-service
```

2. Install dependencies

```bash
pip install -e .
```

3. Run tests

```bash
pytest
```

4. Start the service

```bash
python -m delivery_hours_service.main
```

### Using Docker

1. Build and start the service with Docker Compose

```bash
docker-compose up -d
```

2. The API will be available at <http://localhost:8000>

### Testing with Mock Data

The project includes mock implementations of external services with test data for various venues and cities:

```bash
# Example request
curl "http://localhost:8000/delivery-hours?city_slug=berlin&venue_id=456"
```
