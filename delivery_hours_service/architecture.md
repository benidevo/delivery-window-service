# Delivery Hours Service Architecture and Design Decisions

## High-Level Architecture

I implemented the Delivery Hours Service using a hexagonal architecture pattern that establish a clear boundary between the domain core and external dependencies. This architectural choice was deliberate because it maintains the purity of business logic while isolating external interactions at the boundaries of the system.

The service follows a layered structure with each layer having distinct responsibilities:

- **Domain Layer**: Contains the pure business entities and logic without external dependencies. Here I created models like `Time`, `TimeRange`, `DeliveryWindow`, and `WeeklyDeliveryWindow` that encapsulates the essential rules for delivery time calculations.

- **Application Layer**: Contains the orchestration logic through a use case. My implementation of `GetVenueDeliveryHoursUseCase` coordinates the retrieval of venue opening hours and courier delivery hours, combines them, and produces the final delivery schedule.

- **Infrastructure Layer**: Handles external system interactions through adapter implementations. I created `VenueServiceAdapter` and `CourierServiceAdapter` to connect to their respective external services, and implemented `HttpClient` to manage the actual HTTP communication.

- **Interface Layer**: Exposes the service functionality through a REST endpoint. This layer translates between domain models and the API contract, ensuring proper request validation and response formatting.

## Design Patterns and Principles

I applied several key design patterns and principles in my implementation:

### Circuit Breaker Pattern

I used a circuit breaker pattern to enhance the resilience of external service calls. This pattern prevents cascading failures by opening the circuit after a threshold of failures is reached and periodically testing if the service has recovered. My implementation includes configurable failure thresholds and reset timeouts to fine-tune the resilience behavior.

### Singleton Pattern

I implemented connection pooling for HTTP clients using a singleton pattern through the `HttpClientPool` class. This approach ensures that connections to the same host are reused rather than creating new connections for each request. This significantly reduces resource consumption and improves performance especially under high load. The implementation also maintains a class-level dictionary of clients indexed by base URL, creating new clients only when necessary.

### Result Type Pattern

Rather than relying solely on exceptions for control flow, I created a `DeliveryHoursResult` type that encapsulates both successful outcomes and potential errors. This pattern provides a structured way to aggregate errors from multiple sources while maintaining a clear separation between error handling and business logic.

### Domain-Driven Design

I designed the domain layer following DDD principles with value objects (`Time`), entities (`DeliveryWindow`), and aggregates (`WeeklyDeliveryWindow`). This ensures that business rules are encapsulated within the domain objects themselves, making the code more expressive and aligned with the problem domain.

## Key Trade-offs

### Domain Purity vs. Pragmatism

When designing the domain models, I faced a choice between absolute domain purity and a more pragmatic approach.
I chose strong domain purity, keeping all external concerns out of the domain layer. My domain models like `DeliveryWindow` handle only business logic, while adapters in the infrastructure layer handle the conversion between external data formats and domain objects.
This approach resulted in a cleaner and more testable domain layer, but introduces additional complexity in the form of adapter/converter components. I believe the improved maintainability and testability of the core business logic justifies this additional complexity.

### Asynchronous Execution

The service needs to interact with multiple external systems to fulfill a single request.
I implemented asynchronous calls to external services, allowing them to execute in parallel rather than sequentially.
This significantly improves response times under normal conditions but introduces additional complexity in error handling and results aggregation.

### Not Found as Business Response, Not Error

In my implementation, when a venue or courier is not found, I deliberately treat it as closed for the entire week. I made this design choice because I believe "not found" is an implementation detail that shouldn't leak to clients.
I think about it this way: if we can't deliver to a city where we don't have couriers, it's not an error, instead it's just a business reality. The same applies to venues that don't exist in the system. From a client's perspective, they're simply asking "when can I get delivery?" and the answer is "never". And I think this is a perfectly valid business response, not an error condition.
This is why I return a 200 status code with empty delivery hours rather than a 204 No Content or a 404 Not Found. The request itself was successful, even though the outcome is that delivery isn't available. I believe this approach provides a cleaner, more consistent API that shields clients from internal implementation details.

## Improvement Proposals

### Inter-Service Communication with gRPC

The current implementation uses REST for communication between services. I strongly believe that gRPC would be a more efficient approach for inter-service communication between the services. And this is because gRPC's binary protocol significantly reduces bandwidth usage compared to JSON over HTTP and also supports bidirectional streaming, which could be valuable for future enhancements like real-time delivery hour updates.

### Mock REST API HTTP Status Codes

The current implementation of the mock venue and courier service returns a 404 status code when a venue or city is not found. I think this is a flawed API design. A 404 status code implies a client error i.e. the resource (endpoint) itself does not exist. However, in the context of a typical order fulfillment service, when a venue ID or city is not found, this is not a client error but an implementation detail.

A more appropriate approach would be to return a 200 status code with empty response for courier or venue, or a 204 (No Content) status. This clearly distinguishes between a valid request that yields no results and an invalid endpoint request. The fact that delivery is not possible for a venue ID or city is a valid business outcome, not an error in the client's request.

### Caching Strategy

For production environment, I would implement a caching strategy. Venue opening hours and delivery hours for some cities change infrequently which makes them candidates for caching.

## Challenges Encountered

### Time Range Intersection Complexity

The most intricate challenge I faced was implementing the intersection logic for time ranges, particularly when dealing with overnight windows. Time ranges that cross midnight (e.g., 22:00-02:00) required special handling to correctly calculate their intersections with other time ranges.

My solution involved creating a domain model that explicitly recognizes overnight ranges and handles them differently in intersection calculations. I designed the `TimeRange` class to support both standard and overnight ranges, allowing for clear and concise intersection logic.
This design choice resulted in a more complex domain model but significantly simplified the intersection logic, making it easier to reason about and maintain.

### Time Exception Handling

I found that working with time ranges often led to multiple edge cases that needed careful error handling. I created a dedicated exceptions module in the domain layer that includes specialized time-related exceptions like `InvalidDurationError` and `IncompatibleDaysError`.

This approach helped me clearly communicate what went wrong when time operations failed and allowed the upper layers to handle these failures appropriately. It also made my validation logic more straightforward and self-documenting.

### Error Propagation with Concurrent Execution

Balancing parallel execution of external service calls while maintaining proper error propagation was quite challenging. The approach needed to ensure that errors from one service did not prevent retrieving data from the other service, while still providing meaningful error information to the client.

I resolved this by implementing an error aggregation mechanism in the `DeliveryHoursResult` class, which collects errors from multiple sources while still providing the available data.

## Design Considerations for Scale

### Observability

I've laid the groundwork for comprehensive observability through the implementation of a structured logger. My `StructuredLogger` class outputs JSON-formatted logs with contextual information, making it easy to query and analyze logs in production environments. Each log entry includes timestamps, service name, message, and contextual details that can be used for filtering and aggregation.

The structured logging approach I implemented enables:

- Easy integration with log aggregation tools like Datadog
- Correlation of logs across service boundaries
- Filtering and searching logs by specific attributes
- Analyzing patterns and trends in service behavior

### Data Consistency

The current implementation assumes that venue and courier data is always consistent. In a real-world scenario, I would implement data consistency mechanisms to handle edge cases such as:

- Recently onboarded venues with incomplete data
- Temporary courier service disruptions in specific areas
- Time zone differences and daylight saving time transitions
