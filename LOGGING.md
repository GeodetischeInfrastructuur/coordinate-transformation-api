# Logging Configuration

This application uses structured JSON logging for production-ready observability and monitoring.

## Overview

The logging system is built on:

- **pythonjsonlogger** for structured JSON log formatting
- **Custom middleware** for capturing request metadata
- **Environment variables** for configuration
- **uvicorn** ASGI server with custom logging configuration

All logs are output in JSON format with consistent structure, making them easy to parse and analyze with log aggregation
tools like ELK, Splunk, or CloudWatch.

## Log Output

All logs are written to **stdout** (standard output), following the [twelve-factor app](https://12factor.net/logs)
methodology for cloud-native applications.

**Why stdout?**

- Container-friendly: Docker and Kubernetes capture stdout/stderr automatically
- Flexible routing: Log aggregation tools can capture and route logs without file system access
- No disk I/O: Improves performance and eliminates disk space concerns
- Unified stream: Both application logs and access logs go to the same destination

**Log levels and streams:**

- `DEBUG`, `INFO`: Written to stdout
- `WARNING`, `ERROR`, `CRITICAL`: Written to stderr

This separation allows you to route error logs differently if needed:

```bash
# Run application and separate error logs
./app 2> errors.log

# In Docker, both streams are captured together by default
docker logs container-name
```

**In production environments:**

- Let your container orchestrator (Docker, Kubernetes, ECS) handle log collection
- Use logging drivers (e.g., `json-file`, `journald`, `fluentd`) to route logs
- Configure log aggregation tools to read from container stdout/stderr

## Configuration

Logging is configured through environment variables:

| Environment Variable | Type    | Default | Description                                                                            |
| -------------------- | ------- | ------- | -------------------------------------------------------------------------------------- |
| `LOG_LEVEL`          | string  | `INFO`  | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`                         |
| `ACCESS_LOG`         | boolean | `false` | Enable HTTP access logging                                                             |
| `LOG_FORWARDED_FOR`  | boolean | `false` | Include `X-Forwarded-For` header in access logs (useful behind proxies/load balancers) |

### Example Configuration

```bash
# Development
export LOG_LEVEL=DEBUG
export ACCESS_LOG=true
export LOG_FORWARDED_FOR=false

# Production
export LOG_LEVEL=INFO
export ACCESS_LOG=true
export LOG_FORWARDED_FOR=true
```

## Log Format

### Application Logs

Standard application logs include:

```json
{
  "timestamp": "2025-11-21T10:30:45.123456+00:00",
  "logger": "coordinate_transformation_api.main",
  "level": "INFO",
  "function": "lifespan",
  "line": 95,
  "message": "Application startup complete"
}
```

**Fields:**

- `timestamp`: ISO 8601 formatted UTC timestamp
- `logger`: Python logger name (module path)
- `level`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `function`: Function name where log was generated
- `line`: Line number in source code
- `message`: Log message

### Access Logs

When `ACCESS_LOG=true`, HTTP requests are logged with:

```json
{
  "timestamp": "2025-11-21T10:30:45.123456+00:00",
  "logger": "uvicorn.access",
  "level": "INFO",
  "client_ip": "192.168.1.100",
  "method": "POST",
  "path": "/transform",
  "http_version": "HTTP/1.1",
  "status_code": 200,
  "host": "api.example.com",
  "x_forwarded_for": "203.0.113.42",
  "response_time_ms": 45.23
}
```

**Fields:**

- `timestamp`: ISO 8601 formatted UTC timestamp
- `logger`: Always `uvicorn.access`
- `level`: Always `INFO`
- `client_ip`: Direct client IP address (from connection)
- `method`: HTTP method (GET, POST, etc.)
- `path`: Request path with query string
- `http_version`: HTTP protocol version
- `status_code`: HTTP response status code
- `host`: Value from `Host` header
- `x_forwarded_for`: Value from `X-Forwarded-For` header (only when `LOG_FORWARDED_FOR=true`)
- `response_time_ms`: Request processing time in milliseconds

## Implementation Details

### Architecture

The logging system consists of three main components:

1. **`logging_config.py`**: Core logging configuration

   - `CustomJsonFormatter`: Formats application logs as JSON
   - `AccessLogFormatter`: Formats HTTP access logs as JSON
   - `get_json_logging_config()`: Returns uvicorn-compatible logging configuration

2. **`access_log_middleware.py`**: Request metadata capture

   - `AccessLogMiddleware`: ASGI middleware that captures request details
   - `RequestMetadataFilter`: Logging filter that injects request metadata into log records
   - Thread-local storage for async-safe metadata handling

3. **`main.py`**: Application integration

   - Configures uvicorn with JSON logging
   - Conditionally adds `AccessLogMiddleware` when `ACCESS_LOG=true`

### Thread-Local Storage

Request metadata (Host header, X-Forwarded-For, response time) is stored using `threading.local()` instead of
`contextvars.ContextVar`. This is necessary because uvicorn's access logger runs in a different async context than the
middleware, and thread-local storage bridges this gap reliably.

### Color Codes

The formatters explicitly handle uvicorn's `use_colors` parameter and strip any color-related fields (`color_message`)
to ensure clean JSON output without ANSI escape codes.

## Log Analysis Examples

### Parse JSON logs with jq

```bash
# Show all ERROR level logs
cat app.log | jq 'select(.level == "ERROR")'

# Show access logs with status code >= 400
cat app.log | jq 'select(.status_code >= 400)'

# Calculate average response time
cat app.log | jq -s '[.[] | select(.response_time_ms) | .response_time_ms] | add/length'

# Show all requests from a specific client IP
cat app.log | jq 'select(.client_ip == "192.168.1.100")'

# Show requests taking longer than 1 second
cat app.log | jq 'select(.response_time_ms > 1000)'
```

### Integration with Log Aggregation Tools

The structured JSON format works seamlessly with:

- **ELK Stack (Elasticsearch, Logstash, Kibana)**: Parse as JSON and index all fields
- **AWS CloudWatch Logs Insights**: Automatically parses JSON fields for querying
- **Splunk**: Use `sourcetype=_json` for automatic field extraction
- **Datadog**: JSON logs are automatically parsed and indexed
- **Grafana Loki**: Use JSON parser to extract fields for querying

## Troubleshooting

### Logs not appearing

Check that the log level is appropriate:

```bash
export LOG_LEVEL=DEBUG  # Most verbose
```

### Access logs missing

Ensure access logging is enabled:

```bash
export ACCESS_LOG=true
```

### Missing X-Forwarded-For header

Enable forwarded header logging:

```bash
export LOG_FORWARDED_FOR=true
```

### Host header showing as empty

The Host header should be automatically captured from incoming requests. If it's missing, check that:

1. Your client is sending the `Host` header (all HTTP/1.1 clients must)
2. There's no proxy stripping the header before it reaches the application

### Response time seems inaccurate

Response time is measured using `time.perf_counter()` with millisecond precision. It measures from when the middleware
receives the request until the response is ready to send, so it includes:

- Request parsing
- Application processing
- Response generation

But it does NOT include:

- Network transmission time
- Time spent in reverse proxy/load balancer

## Migration from Old Logging

If you were previously using the `logging.conf` file in the assets folder, that file is no longer used. All logging
configuration now comes from:

1. Environment variables (for user-configurable settings)
2. `logging_config.py` (for format and structure)

The old `logging.conf` file can be safely deleted.

## Development vs Production

### Development

```bash
# More verbose, access logs enabled for debugging
export LOG_LEVEL=DEBUG
export ACCESS_LOG=true
export LOG_FORWARDED_FOR=false
```

### Production

```bash
# Less verbose, access logs enabled for monitoring
export LOG_LEVEL=INFO
export ACCESS_LOG=true
export LOG_FORWARDED_FOR=true  # If behind load balancer
```

### Testing

```bash
# Minimal logging to reduce noise in test output
export LOG_LEVEL=WARNING
export ACCESS_LOG=false
```
