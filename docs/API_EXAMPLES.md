# API Examples

This document provides practical examples of using the Delivery Hours API, including common scenarios and edge cases.

## Basic Usage

### Standard Request

Get delivery hours for a venue in Berlin:

```bash
curl "http://localhost:8000/delivery-hours?city_slug=berlin&venue_id=456"
```

**Response:**

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

### Multiple Cities

Check delivery hours in different cities:

```bash
# London
curl "http://localhost:8000/delivery-hours?city_slug=london&venue_id=123"

# New York
curl "http://localhost:8000/delivery-hours?city_slug=new-york&venue_id=789"
```

## Common Scenarios

### Overnight Delivery Windows

Some venues stay open past midnight, creating delivery windows that span two days:

```bash
curl "http://localhost:8000/delivery-hours?city_slug=berlin&venue_id=789"
```

**Response:**

```json
{
  "delivery_hours": {
    "Monday": "Closed",
    "Tuesday": "20-02",
    "Wednesday": "Closed",
    "Thursday": "Closed",
    "Friday": "18-03",
    "Saturday": "18-03",
    "Sunday": "Closed"
  }
}
```

In this example, Tuesday's delivery window runs from 8 PM Tuesday until 2 AM Wednesday.

### Limited Delivery Hours

When venue hours and courier availability barely overlap:

```bash
curl "http://localhost:8000/delivery-hours?city_slug=madrid&venue_id=456"
```

**Response:**

```json
{
  "delivery_hours": {
    "Monday": "14:30-15",
    "Tuesday": "Closed",
    "Wednesday": "Closed",
    "Thursday": "Closed",
    "Friday": "Closed",
    "Saturday": "Closed",
    "Sunday": "Closed"
  }
}
```

### No Delivery Available

When there's no overlap between venue and courier hours:

```bash
curl "http://localhost:8000/delivery-hours?city_slug=barcelona&venue_id=999"
```

**Response:**

```json
{
  "delivery_hours": {
    "Monday": "Closed",
    "Tuesday": "Closed",
    "Wednesday": "Closed",
    "Thursday": "Closed",
    "Friday": "Closed",
    "Saturday": "Closed",
    "Sunday": "Closed"
  }
}
```

## Error Handling

### Invalid Venue ID

```bash
curl "http://localhost:8000/delivery-hours?city_slug=berlin&venue_id=invalid"
```

**Response:**

```json
{
  "detail": "Venue not found"
}
```

### Missing Parameters

```bash
curl "http://localhost:8000/delivery-hours?city_slug=berlin"
```

**Response:**

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["query", "venue_id"],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

### Service Unavailable

When external services are down, the API returns graceful error responses:

```bash
curl "http://localhost:8000/delivery-hours?city_slug=offline-city&venue_id=123"
```

**Response:**

```json
{
  "detail": "Unable to retrieve delivery hours at this time. Please try again later."
}
```

## Health Check

Check if the service is running properly:

```bash
curl "http://localhost:8000/health"
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "checks": {
    "venue_service": "ok",
    "courier_service": "ok"
  }
}
```

## Performance Testing

### Load Testing with Multiple Requests

```bash
# Test concurrent requests
for i in {1..10}; do
  curl "http://localhost:8000/delivery-hours?city_slug=berlin&venue_id=456" &
done
wait
```

### Response Time Measurement

```bash
curl -w "@-" -o /dev/null -s "http://localhost:8000/delivery-hours?city_slug=berlin&venue_id=456" <<'EOF'
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
EOF
```

## Integration Examples

### Using with jq for JSON Processing

```bash
# Extract only Monday's hours
curl -s "http://localhost:8000/delivery-hours?city_slug=berlin&venue_id=456" | \
  jq -r '.delivery_hours.Monday'

# Check if venue is open on weekends
curl -s "http://localhost:8000/delivery-hours?city_slug=berlin&venue_id=456" | \
  jq '.delivery_hours | {Saturday, Sunday}'
```

### Python Integration

```python
import requests

response = requests.get(
    "http://localhost:8000/delivery-hours",
    params={"city_slug": "berlin", "venue_id": "456"}
)

if response.status_code == 200:
    delivery_hours = response.json()["delivery_hours"]
    print(f"Monday hours: {delivery_hours['Monday']}")
else:
    print(f"Error: {response.status_code}")
```

## Business Logic Examples

### 30-Minute Minimum Rule

The service enforces a 30-minute minimum delivery window:

```bash
# This venue would have a 25-minute window, so it shows as "Closed"
curl "http://localhost:8000/delivery-hours?city_slug=short-window&venue_id=123"
```

**Response:**

```json
{
  "delivery_hours": {
    "Monday": "Closed",
    "Tuesday": "Closed",
    "Wednesday": "Closed",
    "Thursday": "Closed",
    "Friday": "Closed",
    "Saturday": "Closed",
    "Sunday": "Closed"
  }
}
```

### Complex Time Intersections

When venues have split hours that partially overlap with courier availability:

```bash
curl "http://localhost:8000/delivery-hours?city_slug=complex&venue_id=456"
```

**Response:**

```json
{
  "delivery_hours": {
    "Monday": "13:30-14, 17-20",
    "Tuesday": "Closed",
    "Wednesday": "Closed",
    "Thursday": "Closed",
    "Friday": "Closed",
    "Saturday": "Closed",
    "Sunday": "Closed"
  }
}
```

This shows a venue with lunch (13:30-15:00) and dinner (16:00-21:00) hours, where courier service is available 09:00-14:00 and 17:00-20:00.
