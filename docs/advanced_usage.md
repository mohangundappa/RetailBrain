# Advanced Usage Guide

## Overview

This guide provides advanced techniques and best practices for optimizing, testing, and scaling the Staples Brain multi-agent platform. It's intended for experienced developers and system architects who need to extend the platform beyond basic usage.

## Agent Validation Framework

### Comprehensive Testing

To ensure agent reliability, implement a comprehensive validation framework:

```python
async def validate_agent(agent_id: str, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Run comprehensive validation tests on an agent.
    
    Args:
        agent_id: ID of the agent to validate
        test_cases: List of test cases with input messages and expected outcomes
        
    Returns:
        Validation results with metrics
    """
    results = {
        "passed": 0,
        "failed": 0,
        "metrics": {
            "avg_response_time_ms": 0,
            "avg_confidence": 0,
            "routing_accuracy": 0
        },
        "test_results": []
    }
    
    total_response_time = 0
    total_confidence = 0
    
    for test_case in test_cases:
        # Execute test
        start_time = time.time()
        response = await execute_agent_direct(
            agent_id=agent_id,
            message=test_case["input"],
            context=test_case.get("context", {})
        )
        response_time = (time.time() - start_time) * 1000
        
        # Process results
        passed = evaluate_response(response, test_case["expected"])
        
        # Record metrics
        total_response_time += response_time
        total_confidence += response.get("metadata", {}).get("confidence", 0)
        
        # Record test result
        results["test_results"].append({
            "input": test_case["input"],
            "expected": test_case["expected"],
            "actual": response["response"]["message"],
            "passed": passed,
            "response_time_ms": response_time,
            "confidence": response.get("metadata", {}).get("confidence", 0)
        })
        
        # Update counters
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Calculate averages
    test_count = len(test_cases)
    results["metrics"]["avg_response_time_ms"] = total_response_time / test_count
    results["metrics"]["avg_confidence"] = total_confidence / test_count
    results["metrics"]["routing_accuracy"] = results["passed"] / test_count
    
    return results
```

### Example Test Case Definition

```json
{
  "test_cases": [
    {
      "name": "Basic password reset request",
      "input": "I need to reset my password",
      "expected": {
        "intent": "reset_password",
        "entities": [],
        "confidence_min": 0.7,
        "response_contains": ["email", "account", "reset"]
      },
      "context": {}
    },
    {
      "name": "Password reset with known email",
      "input": "I forgot my password for user@example.com",
      "expected": {
        "intent": "reset_password",
        "entities": ["email"],
        "confidence_min": 0.8,
        "response_contains": ["verification", "code", "sent"]
      },
      "context": {}
    }
  ]
}
```

## Performance Optimization

### Agent Selection Optimization

The agent selection process can be optimized for high-throughput systems:

1. **Pattern Caching**

```python
class CachedPatternStore:
    """Pattern store with caching for high-performance matching."""
    
    def __init__(self):
        self.patterns = {}
        self.pattern_cache = LRUCache(maxsize=1000)
    
    def add_pattern(self, agent_id: str, pattern: PatternCapability):
        """Add a pattern to the store."""
        if agent_id not in self.patterns:
            self.patterns[agent_id] = []
        self.patterns[agent_id].append(pattern)
    
    def match(self, query: str) -> List[Tuple[str, float]]:
        """Match query against patterns with caching."""
        # Check cache first
        cache_key = self._hash_query(query)
        cached_result = self.pattern_cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Perform matching
        matches = []
        for agent_id, agent_patterns in self.patterns.items():
            for pattern in agent_patterns:
                if re.search(pattern.regex, query, re.IGNORECASE):
                    matches.append((agent_id, pattern.confidence))
                    break
        
        # Sort by confidence
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Cache result
        self.pattern_cache[cache_key] = matches
        
        return matches
    
    def _hash_query(self, query: str) -> str:
        """Generate a hash for the query."""
        # Normalize query
        normalized = query.lower().strip()
        # Generate hash
        return hashlib.md5(normalized.encode()).hexdigest()
```

2. **Parallel Semantic Search**

```python
async def parallel_semantic_search(query: str, agent_ids: List[str]) -> List[Tuple[str, float]]:
    """
    Execute semantic search in parallel for better performance.
    
    Args:
        query: User query
        agent_ids: List of agent IDs to search
        
    Returns:
        List of (agent_id, similarity) tuples
    """
    # Get query embedding
    query_embedding = await get_embedding(query)
    
    # Create search tasks
    search_tasks = []
    for agent_id in agent_ids:
        task = asyncio.create_task(
            search_agent_vectors(agent_id, query_embedding)
        )
        search_tasks.append(task)
    
    # Wait for all searches to complete
    results = await asyncio.gather(*search_tasks)
    
    # Flatten and sort results
    flat_results = []
    for agent_id, similarities in zip(agent_ids, results):
        if similarities:
            flat_results.append((agent_id, max(similarities)))
    
    return sorted(flat_results, key=lambda x: x[1], reverse=True)
```

### Memory Optimization

For high-traffic systems, optimize memory usage:

```python
class TieredMemoryService:
    """
    Tiered memory service with different storage strategies based on scope.
    
    This provides optimized storage with:
    - In-memory cache for working memory (fastest)
    - Redis for short-term memory (fast)
    - PostgreSQL for long-term memory (persistent)
    """
    
    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        db_session: Optional[AsyncSession] = None
    ):
        """Initialize the tiered memory service."""
        self.working_memory = {}  # In-memory cache
        self.redis_client = redis_client
        self.db_session = db_session
    
    async def store(
        self,
        session_id: str,
        memory_type: str,
        content: str,
        scope: str = "short_term",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store memory with tiered approach based on scope."""
        entry_id = str(uuid.uuid4())
        
        if scope == "working":
            # Store in-memory for fastest access
            key = f"{session_id}:{memory_type}:{entry_id}"
            self.working_memory[key] = {
                "content": content,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat()
            }
        elif scope == "short_term" and self.redis_client:
            # Store in Redis for fast access
            key = f"memory:{session_id}:{memory_type}:{entry_id}"
            await self.redis_client.set(
                key,
                json.dumps({
                    "content": content,
                    "metadata": metadata or {},
                    "timestamp": datetime.now().isoformat()
                }),
                ex=86400  # Expire after 24 hours
            )
        else:
            # Store in database for persistence
            await self._store_in_db(
                session_id,
                memory_type,
                entry_id,
                content,
                scope,
                metadata
            )
        
        return entry_id
    
    async def retrieve(
        self,
        session_id: str,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retrieve memories from tiered storage."""
        results = []
        
        # Check working memory (in-memory)
        for key, value in self.working_memory.items():
            if key.startswith(f"{session_id}:"):
                if memory_type and not key.startswith(f"{session_id}:{memory_type}:"):
                    continue
                results.append({
                    "id": key.split(":")[-1],
                    "type": key.split(":")[1],
                    "content": value["content"],
                    "metadata": value["metadata"],
                    "timestamp": value["timestamp"],
                    "source": "working_memory"
                })
        
        # Check short-term memory (Redis)
        if self.redis_client:
            pattern = f"memory:{session_id}:*" if not memory_type else f"memory:{session_id}:{memory_type}:*"
            redis_keys = await self.redis_client.keys(pattern)
            for redis_key in redis_keys[:limit - len(results)]:
                value = await self.redis_client.get(redis_key)
                if value:
                    data = json.loads(value)
                    results.append({
                        "id": redis_key.decode().split(":")[-1],
                        "type": redis_key.decode().split(":")[2],
                        "content": data["content"],
                        "metadata": data["metadata"],
                        "timestamp": data["timestamp"],
                        "source": "redis"
                    })
        
        # Check long-term memory (Database)
        if len(results) < limit and self.db_session:
            db_results = await self._retrieve_from_db(
                session_id,
                memory_type,
                limit - len(results)
            )
            results.extend(db_results)
        
        # Sort by timestamp (newest first)
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return results[:limit]
```

## Scaling Guidelines

### Horizontal Scaling Architecture

For high-volume deployments, implement a horizontally scalable architecture:

```
                   ┌─────────────────┐
                   │ Load Balancer   │
                   └─────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
    ┌─────────▼─────────┐     ┌─────────▼─────────┐
    │ API Gateway Node 1 │     │ API Gateway Node 2 │
    └─────────┬─────────┘     └─────────┬─────────┘
              │                         │
              │                         │
    ┌─────────▼─────────┐     ┌─────────▼─────────┐
    │ Brain Service 1   │     │ Brain Service 2   │
    └─────────┬─────────┘     └─────────┬─────────┘
              │                         │
              └────────────┬────────────┘
                           │
                 ┌─────────▼─────────┐
                 │ Shared Redis Cache│
                 └─────────┬─────────┘
                           │
                 ┌─────────▼─────────┐
                 │ PostgreSQL Cluster│
                 └───────────────────┘
```

### Scaling Recommendations

1. **Stateless API Gateway**
   - Make API Gateway nodes stateless for easy scaling
   - Use distributed tracing for request tracking

2. **Distributed Brain Service**
   - Maintain brain service state in shared Redis/PostgreSQL
   - Implement concurrent request limiting to prevent LLM overloading

3. **Database Scaling**
   - Use read replicas for high-read workloads
   - Implement connection pooling for efficient DB usage
   - Consider partitioning for very large deployments

4. **Memory Service Scaling**
   - Use Redis cluster for distributed caching
   - Implement tiered storage based on access patterns

## Advanced Monitoring

### Telemetry Implementation

Implement comprehensive telemetry for system health monitoring:

```python
class TelemetryService:
    """Service for collecting and reporting system telemetry."""
    
    def __init__(
        self,
        db_session: AsyncSession,
        metrics_client: Optional[Any] = None
    ):
        """Initialize the telemetry service."""
        self.db_session = db_session
        self.metrics_client = metrics_client
    
    async def record_agent_selection(
        self,
        session_id: str,
        query: str,
        selected_agent: str,
        confidence: float,
        selection_method: str,
        processing_time_ms: float
    ) -> str:
        """Record agent selection event."""
        # Create trace ID
        trace_id = str(uuid.uuid4())
        
        # Record in database
        stmt = insert(AgentSelectionEvent).values(
            trace_id=trace_id,
            session_id=session_id,
            query=query,
            selected_agent=selected_agent,
            confidence=confidence,
            selection_method=selection_method,
            processing_time_ms=processing_time_ms,
            timestamp=datetime.now()
        )
        await self.db_session.execute(stmt)
        await self.db_session.commit()
        
        # Send to metrics system if available
        if self.metrics_client:
            self.metrics_client.gauge(
                "agent_selection_confidence",
                confidence,
                tags={
                    "agent": selected_agent,
                    "method": selection_method
                }
            )
            self.metrics_client.timing(
                "agent_selection_processing_time",
                processing_time_ms,
                tags={
                    "agent": selected_agent,
                    "method": selection_method
                }
            )
        
        return trace_id
    
    async def record_agent_execution(
        self,
        trace_id: str,
        agent_id: str,
        success: bool,
        error: Optional[str] = None,
        execution_time_ms: float = 0,
        tool_executions: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Record agent execution event."""
        # Record in database
        stmt = insert(AgentExecutionEvent).values(
            trace_id=trace_id,
            agent_id=agent_id,
            success=success,
            error=error,
            execution_time_ms=execution_time_ms,
            tool_executions=tool_executions,
            timestamp=datetime.now()
        )
        await self.db_session.execute(stmt)
        await self.db_session.commit()
        
        # Send to metrics system if available
        if self.metrics_client:
            self.metrics_client.increment(
                "agent_execution_count",
                tags={
                    "agent": agent_id,
                    "success": str(success)
                }
            )
            self.metrics_client.timing(
                "agent_execution_time",
                execution_time_ms,
                tags={
                    "agent": agent_id,
                    "success": str(success)
                }
            )
```

### Performance Dashboards

Implement dashboards for monitoring:

1. **Agent Selection Metrics**
   - Selection method distribution
   - Confidence score averages
   - Pattern vs. semantic selection ratio
   - Fallback occurrences

2. **Response Time Tracking**
   - End-to-end latency
   - Component-level timing
   - Bottleneck identification

3. **Error Rate Monitoring**
   - Agent failures
   - LLM service errors
   - Database connectivity issues

## Advanced Agent Patterns

### Ensemble Agents

Implement ensemble agents that combine responses from multiple specialized agents:

```python
class EnsembleAgent(BaseAgent):
    """
    Agent that combines results from multiple specialized agents.
    This improves response quality by leveraging multiple perspectives.
    """
    
    def __init__(
        self,
        agent_definition: AgentDefinition,
        db_session: AsyncSession,
        component_agents: List[str]
    ):
        """Initialize the ensemble agent."""
        super().__init__(agent_definition, db_session)
        self.component_agents = component_agents
        
    async def process_message(
        self,
        message: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process message using ensemble of agents.
        
        Args:
            message: User message
            session_id: Session identifier
            context: Additional context
            
        Returns:
            Response dictionary
        """
        # Get responses from component agents
        agent_responses = []
        for agent_id in self.component_agents:
            response = await self._get_agent_response(
                agent_id=agent_id,
                message=message,
                session_id=session_id,
                context=context
            )
            agent_responses.append(response)
        
        # Synthesize final response
        synthesized_response = await self._synthesize_responses(
            message=message,
            agent_responses=agent_responses,
            context=context
        )
        
        return {
            "success": True,
            "response": synthesized_response,
            "agent": self.name,
            "metadata": {
                "component_agents": self.component_agents,
                "is_ensemble": True
            }
        }
    
    async def _synthesize_responses(
        self,
        message: str,
        agent_responses: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Synthesize responses from multiple agents."""
        # Build prompt with all responses
        prompt = f"User message: {message}\n\n"
        for i, response in enumerate(agent_responses):
            prompt += f"Agent {i+1} response: {response.get('response', '')}\n\n"
        
        prompt += "Synthesize these responses into a single coherent answer:"
        
        # Get synthesized response from LLM
        llm_response = await self.llm.agenerate(prompt=prompt)
        return llm_response
```

### Human-in-the-Loop Agents

For critical operations, implement agents that can defer to human operators:

```python
class HumanInTheLoopAgent(BaseAgent):
    """
    Agent that can defer decisions to human operators for complex cases.
    """
    
    def __init__(
        self,
        agent_definition: AgentDefinition,
        db_session: AsyncSession,
        confidence_threshold: float = 0.7,
        human_queue_service: Any = None
    ):
        """Initialize the human-in-the-loop agent."""
        super().__init__(agent_definition, db_session)
        self.confidence_threshold = confidence_threshold
        self.human_queue_service = human_queue_service
    
    async def process_message(
        self,
        message: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process message with human fallback option."""
        # Initial automated processing
        automated_response, confidence = await self._get_automated_response(
            message=message,
            context=context
        )
        
        # Decide if human review is needed
        if confidence < self.confidence_threshold:
            # Queue for human review
            review_id = await self._queue_for_human_review(
                message=message,
                session_id=session_id,
                automated_response=automated_response,
                confidence=confidence,
                context=context
            )
            
            # Return interim response
            return {
                "success": True,
                "response": "Your request requires additional review. Our team will respond shortly.",
                "agent": self.name,
                "metadata": {
                    "requires_human_review": True,
                    "review_id": review_id,
                    "confidence": confidence
                }
            }
        
        # Return automated response
        return {
            "success": True,
            "response": automated_response,
            "agent": self.name,
            "metadata": {
                "requires_human_review": False,
                "confidence": confidence
            }
        }
    
    async def _queue_for_human_review(
        self,
        message: str,
        session_id: str,
        automated_response: str,
        confidence: float,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Queue message for human review."""
        if not self.human_queue_service:
            raise ValueError("Human queue service not configured")
        
        # Create review record
        review_id = str(uuid.uuid4())
        await self.human_queue_service.add_to_queue({
            "review_id": review_id,
            "message": message,
            "session_id": session_id,
            "automated_response": automated_response,
            "confidence": confidence,
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "status": "pending_review"
        })
        
        return review_id
```

## Security Enhancements

### Advanced Agent Guardrails

Implement robust security guardrails:

```python
class EnhancedGuardrailsService:
    """
    Enhanced security guardrails for agent responses.
    Implements multiple levels of content filtering.
    """
    
    def __init__(
        self,
        llm: Any,
        security_policies: Optional[Dict[str, Any]] = None,
        content_filter: Optional[Any] = None
    ):
        """Initialize enhanced guardrails service."""
        self.llm = llm
        self.security_policies = security_policies or self._default_policies()
        self.content_filter = content_filter
    
    async def check_response(
        self,
        response: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Check if response meets security and quality standards.
        
        Args:
            response: Response to check
            context: Additional context
            
        Returns:
            Tuple of (passed, filtered_response, details)
        """
        results = {}
        
        # Apply content filter if available
        if self.content_filter:
            filter_result = await self.content_filter.check_content(response)
            results["content_filter"] = filter_result
            
            if not filter_result["safe"]:
                return False, self._get_fallback_response(
                    issue="content_policy",
                    context=context
                ), results
        
        # Apply policy checks
        policy_results = await self._apply_policy_checks(response, context)
        results["policy_checks"] = policy_results
        
        # Check if all policies passed
        all_passed = all(check["passed"] for check in policy_results.values())
        
        if all_passed:
            return True, response, results
        
        # Find the first failed check
        failed_policy = next(
            (policy for policy, check in policy_results.items() if not check["passed"]),
            "unknown"
        )
        
        return False, self._get_fallback_response(
            issue=failed_policy,
            context=context
        ), results
    
    async def _apply_policy_checks(
        self,
        response: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Apply all policy checks to the response."""
        results = {}
        
        # Apply each policy check
        for policy_name, policy in self.security_policies.items():
            check_result = await self._apply_single_policy(
                policy_name=policy_name,
                policy=policy,
                response=response,
                context=context
            )
            results[policy_name] = check_result
        
        return results
    
    async def _apply_single_policy(
        self,
        policy_name: str,
        policy: Dict[str, Any],
        response: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Apply a single policy check."""
        check_method = policy.get("method", "llm")
        
        if check_method == "regex":
            # Check using regex pattern
            pattern = policy["pattern"]
            should_match = policy.get("should_match", False)
            
            match_found = bool(re.search(pattern, response))
            passed = match_found if should_match else not match_found
            
            return {
                "passed": passed,
                "method": "regex",
                "details": {
                    "match_found": match_found,
                    "should_match": should_match
                }
            }
        
        elif check_method == "llm":
            # Check using LLM
            prompt = policy["prompt"].format(
                response=response,
                **context or {}
            )
            
            llm_response = await self.llm.agenerate(prompt=prompt)
            # Parse LLM response (expected: "YES" or "NO")
            passed = "YES" in llm_response.upper()
            
            return {
                "passed": passed,
                "method": "llm",
                "details": {
                    "llm_response": llm_response
                }
            }
        
        else:
            raise ValueError(f"Unknown policy check method: {check_method}")
    
    def _get_fallback_response(
        self,
        issue: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get fallback response for failed checks."""
        fallbacks = {
            "content_policy": "I apologize, but I cannot provide that information as it conflicts with our content policies.",
            "accuracy": "I apologize, but I can't provide a sufficiently accurate answer to that question.",
            "brand_voice": "I apologize, but I'm unable to respond to that request in an appropriate manner.",
            "unknown": "I apologize, but I'm unable to provide a response to that request."
        }
        
        return fallbacks.get(issue, fallbacks["unknown"])
    
    def _default_policies(self) -> Dict[str, Any]:
        """Get default security policies."""
        return {
            "accuracy": {
                "method": "llm",
                "prompt": "Does the following response contain only factually accurate information? If you are not certain the information is accurate, respond with NO. If you're confident the information is accurate, respond with YES.\n\nResponse: {response}\n\nIs this response factually accurate? (YES/NO)"
            },
            "brand_voice": {
                "method": "llm",
                "prompt": "Does the following response maintain a professional, helpful tone appropriate for a customer service representative? Please answer YES or NO.\n\nResponse: {response}\n\nIs this response professionally appropriate? (YES/NO)"
            }
        }
```

## Conclusion

This advanced usage guide provides techniques for optimizing, scaling, and enhancing the Staples Brain platform for enterprise-grade deployments. By implementing these patterns and best practices, you can ensure high performance, reliability, and security for your multi-agent system.

For further assistance with advanced implementations, contact the platform architecture team.