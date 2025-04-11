# Circuit Breaker Pattern: Developer's Guide

## Overview

This document provides a detailed technical overview of the Circuit Breaker pattern implementation in the Staples Brain platform. It covers the architecture, components, usage patterns, and API reference for developers working with or extending the system.

## Architecture

The Circuit Breaker implementation follows a modular approach with these key components:

1. **Circuit Breaker Utility (`utils/circuit_breaker.py`)** - Core implementation of the circuit breaker pattern
2. **Circuit Breaker Registry** - Central registry for all circuit breakers in the system
3. **Base API Client Integration** - Integration with the base API client for automatic protection
4. **Circuit Breaker API** - REST API for monitoring and controlling circuit breakers

![Circuit Breaker Architecture](/docs/architecture/circuit_breaker_architecture.svg)

## Circuit Breaker States

A circuit breaker can be in one of three states:

1. **Closed (Normal Operation)** - Calls are allowed to pass through to the external service
2. **Open (Service Unavailable)** - Calls are prevented from reaching the external service
3. **Half-Open (Testing Recovery)** - A limited number of calls are allowed to test if the service has recovered

![Circuit Breaker State Diagram](docs/architecture/circuit_breaker_state_diagram.svg)

## Implementation Details

### Circuit Breaker Utility

The core implementation is in `utils/circuit_breaker.py` and includes:

```python
class CircuitBreaker:
    def __init__(self, name, failure_threshold=5, recovery_timeout=30):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"
        
    def execute(self, func, fallback_func=None):
        # Check if circuit is open
        if self.state == "open":
            if self._should_attempt_recovery():
                self.state = "half-open"
            else:
                # Circuit is open, use fallback
                if fallback_func:
                    return fallback_func()
                raise CircuitBreakerOpenException(f"Circuit '{self.name}' is open")
                
        try:
            # Execute the function
            result = func()
            
            # If successful in half-open state, reset the circuit
            if self.state == "half-open":
                self._reset()
                
            return result
            
        except Exception as e:
            # Record failure
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            # Check if threshold exceeded
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                
            # Re-raise or use fallback
            if fallback_func:
                return fallback_func()
            raise e
```

### Circuit Breaker Registry

The registry provides centralized access to all circuit breakers:

```python
class CircuitBreakerRegistry:
    def __init__(self):
        self._circuit_breakers = {}
        
    def register(self, circuit_breaker):
        self._circuit_breakers[circuit_breaker.name] = circuit_breaker
        
    def get(self, name):
        return self._circuit_breakers.get(name)
        
    def reset(self, name):
        circuit_breaker = self.get(name)
        if circuit_breaker:
            circuit_breaker._reset()
            return True
        return False
        
    def get_all_circuit_states(self):
        states = {}
        for name, cb in self._circuit_breakers.items():
            states[name] = cb.get_state()
        return states
```

### API Client Integration

The base API client (`api_services/base_api_client.py`) integrates with the circuit breaker:

```python
def _make_request(self, method, endpoint, params=None, data=None, mock_response=None):
    # Get or create circuit breaker for this service
    circuit_name = f"{self.service_name}_circuit"
    circuit = circuit_breaker_registry.get(circuit_name)
    
    if not circuit:
        circuit = CircuitBreaker(
            name=circuit_name,
            failure_threshold=self.failure_threshold,
            recovery_timeout=self.recovery_timeout
        )
        circuit_breaker_registry.register(circuit)
    
    # Define the request function
    def make_live_request():
        # Make the actual API request
        # ...
    
    # Define the fallback function
    def fallback_function():
        # Return mock data or error response
        # ...
    
    # Execute with circuit breaker protection
    return circuit.execute(make_live_request, fallback_function)
```

## REST API Reference

### Get All Circuit Breakers

`GET /api/circuit-breakers`

Sample Response:
```json
{
    "success": true,
    "circuit_breakers": {
        "order-api_circuit": {
            "name": "order-api_circuit",
            "state": "closed",
            "failure_count": 0,
            "failure_threshold": 5,
            "recovery_timeout": 30,
            "last_failure_time": 0,
            "time_remaining": 0
        },
        "store-api_circuit": {
            "name": "store-api_circuit",
            "state": "closed",
            "failure_count": 0,
            "failure_threshold": 5,
            "recovery_timeout": 30,
            "last_failure_time": 0,
            "time_remaining": 0
        }
    }
}
```

### Get Specific Circuit Breaker

`GET /api/circuit-breakers/{name}`

Sample Response:
```json
{
    "success": true,
    "circuit_breaker": {
        "name": "order-api_circuit",
        "state": "closed",
        "failure_count": 0,
        "failure_threshold": 5,
        "recovery_timeout": 30,
        "last_failure_time": 0,
        "time_remaining": 0
    }
}
```

### Reset Circuit Breaker

`POST /api/circuit-breakers/{name}/reset`

Sample Response:
```json
{
    "success": true,
    "message": "Circuit breaker 'order-api_circuit' reset successfully"
}
```

## Usage Examples

### Using Circuit Breakers in New API Clients

```python
from utils.circuit_breaker import CircuitBreaker, circuit_breaker_registry

class MyApiClient:
    def __init__(self, service_name="my-api", failure_threshold=5, recovery_timeout=30):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
    
    def make_api_call(self):
        # Get or create circuit breaker
        circuit_name = f"{self.service_name}_circuit"
        circuit = circuit_breaker_registry.get(circuit_name)
        
        if not circuit:
            circuit = CircuitBreaker(
                name=circuit_name,
                failure_threshold=self.failure_threshold,
                recovery_timeout=self.recovery_timeout
            )
            circuit_breaker_registry.register(circuit)
        
        # Define functions
        def api_call():
            # Make actual API call
            return response
            
        def fallback():
            # Return fallback data
            return default_data
            
        # Execute with protection
        return circuit.execute(api_call, fallback)
```

### Monitoring Circuit Breaker Status

```python
import requests

# Get all circuit breakers
response = requests.get("http://localhost:5000/api/circuit-breakers")
circuit_breakers = response.json()["circuit_breakers"]

# Check for open circuits
open_circuits = [name for name, data in circuit_breakers.items() if data["state"] == "open"]
if open_circuits:
    print(f"Warning: The following circuits are open: {', '.join(open_circuits)}")
```

## Best Practices

1. **Appropriate Thresholds**: Set failure thresholds based on the criticality and expected reliability of the external service.
2. **Reasonable Timeouts**: Set recovery timeouts appropriate to the service - longer for critical services that need time to recover, shorter for services where quick recovery is expected.
3. **Meaningful Fallbacks**: Provide useful fallback responses rather than generic errors.
4. **Monitor Circuit Status**: Regularly check circuit breaker states as part of system monitoring.
5. **Log Circuit Events**: Log when circuits open, close, or enter half-open state for debugging.

## Troubleshooting

### Circuit Breaker Won't Reset

If a circuit breaker remains open even after the recovery timeout has passed:

1. Check if the external service is truly recovered using direct API tests
2. Use the reset endpoint: `POST /api/circuit-breakers/{name}/reset`
3. Verify the circuit state after reset: `GET /api/circuit-breakers/{name}`

### Too Many Open Circuits

If you're seeing too many circuits opening:

1. Adjust the failure threshold to be more lenient
2. Check the external service for issues
3. Review error handling in the API client

## Future Enhancements

Planned enhancements to the Circuit Breaker implementation include:

1. **Adaptive Timeouts**: Dynamically adjust timeouts based on service performance
2. **Circuit Breaker Dashboard**: Web UI for monitoring and managing circuit breakers
3. **Notification System**: Alert when circuits open or close
4. **Historical Data**: Track circuit breaker performance over time