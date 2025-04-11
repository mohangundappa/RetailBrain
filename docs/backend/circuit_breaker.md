# Circuit Breaker Pattern

## Overview

This document provides a consolidated view of the Circuit Breaker pattern implemented in Staples Brain. It combines information from both the executive summary and technical guide.

## Purpose

The Circuit Breaker pattern is designed to:

1. Prevent cascading failures when external services are unavailable
2. Provide graceful degradation of functionality
3. Automatically recover when services become available again
4. Collect telemetry on service health

## Implementation

The Staples Brain implementation uses a state machine with three states:

1. **Closed**: Normal operation, requests flow through
2. **Open**: External service is considered unavailable, requests fail fast
3. **Half-Open**: Testing if the service has recovered

![Circuit Breaker State Diagram](./architecture_diagrams/circuit_breaker_state_diagram.svg)

## Configuration

Circuit breakers can be configured with the following parameters:

- Failure threshold: Number of failures before opening
- Timeout duration: How long to keep the circuit open
- Half-open request count: Number of test requests in half-open state

## Usage in Staples Brain

Circuit breakers are used to protect:

1. External API calls to order tracking systems
2. Store location service calls
3. Authentication service interactions

## Monitoring

The circuit breaker status is exposed through:

1. Telemetry events logged to the database
2. Prometheus metrics
3. Health check endpoint status

## References

- [Executive Summary](./circuit_breaker_executive_summary.md)
- [Technical Guide](./circuit_breaker_technical_guide.md)
- [Architecture Diagrams](./architecture_diagrams/)