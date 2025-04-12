"""
Benchmark the agent selection performance.
This script measures the performance of the optimized agent selection implementation.
"""
import json
import os
import time
import uuid
import requests
import random
import csv
from datetime import datetime

# Base URL for API
BASE_URL = "http://localhost:5000/api/v1"
STANDARD_CHAT_URL = f"{BASE_URL}/chat"
OPTIMIZED_CHAT_URL = f"{BASE_URL}/optimized/chat"  # Legacy route kept for backward compatibility

# Test queries for different intents
QUERIES = {
    "password_reset": [
        "I need to reset my password",
        "Forgot my password",
        "Can't log into my account",
        "How do I change my password?",
        "Reset my account credentials"
    ],
    "order_tracking": [
        "Where is my order?",
        "Track my package",
        "Order status for #12345",
        "Has my order shipped yet?",
        "Check delivery status"
    ],
    "store_location": [
        "Find a Staples store near me",
        "Where is the closest Staples?",
        "Staples locations in Chicago",
        "Is there a Staples in downtown?",
        "Find store in zip code 90210"
    ]
}

def run_benchmark(num_iterations=5):
    """
    Run a benchmark of the agent selection performance.
    
    Args:
        num_iterations: Number of iterations per query type
        
    Returns:
        Dictionary with benchmark results
    """
    results = {
        "standard": {
            "total_time": 0,
            "total_queries": 0,
            "selection_time": 0,
            "agent_selection": {}
        }
    }
    
    # Prepare test data
    test_queries = []
    for intent, queries in QUERIES.items():
        for query in queries:
            for _ in range(num_iterations):
                test_queries.append((intent, query))
    
    # Shuffle queries to simulate realistic usage
    random.shuffle(test_queries)
    
    print(f"Running benchmark with {len(test_queries)} total queries...")
    
    # Run tests on the standard endpoint
    print("\nTesting standard chat endpoint...")
    for i, (intent, query) in enumerate(test_queries):
        session_id = str(uuid.uuid4())
        print(f"  Query {i+1}/{len(test_queries)}: {query[:30]}...")
        
        start_time = time.time()
        response = requests.post(
            STANDARD_CHAT_URL,
            json={"message": query, "session_id": session_id}
        )
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            agent = result.get("agent", "unknown")
            metadata = result.get("metadata", {})
            selection_time = metadata.get("selection_time", 0) if metadata else 0
            
            # Update results
            results["standard"]["total_time"] += elapsed
            results["standard"]["total_queries"] += 1
            results["standard"]["selection_time"] += selection_time
            
            # Track agent selection
            if agent not in results["standard"]["agent_selection"]:
                results["standard"]["agent_selection"][agent] = 0
            results["standard"]["agent_selection"][agent] += 1
    
    # Calculate averages
    if results["standard"]["total_queries"] > 0:
        results["standard"]["avg_time"] = results["standard"]["total_time"] / results["standard"]["total_queries"]
        results["standard"]["avg_selection_time"] = results["standard"]["selection_time"] / results["standard"]["total_queries"]
    
    return results

def print_results(results):
    """Print the benchmark results in a readable format."""
    print("\n=== Benchmark Results ===")
    
    # Standard route results
    print("\nStandard Chat API Results:")
    print(f"  Total queries: {results['standard']['total_queries']}")
    print(f"  Total time: {results['standard']['total_time']:.2f} seconds")
    if 'avg_time' in results['standard']:
        print(f"  Average time per query: {results['standard']['avg_time']:.2f} seconds")
    if 'avg_selection_time' in results['standard']:
        print(f"  Average selection time: {results['standard']['avg_selection_time']:.2f} seconds")
    
    print("  Agent selection distribution:")
    for agent, count in results['standard']['agent_selection'].items():
        percentage = (count / results['standard']['total_queries']) * 100
        print(f"    {agent}: {count} ({percentage:.1f}%)")

def save_results_to_csv(results):
    """Save benchmark results to a CSV file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"benchmark_results_{timestamp}.csv"
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(["Metric", "Standard Chat API"])
        
        # Write data
        total_queries = results['standard']['total_queries']
        writer.writerow(["Total Queries", total_queries])
        
        total_time = results['standard']['total_time']
        writer.writerow(["Total Time (s)", f"{total_time:.2f}"])
        
        if 'avg_time' in results['standard']:
            avg_time = results['standard']['avg_time']
            writer.writerow(["Avg Time Per Query (s)", f"{avg_time:.2f}"])
        
        if 'avg_selection_time' in results['standard']:
            writer.writerow(["Avg Selection Time (s)", f"{results['standard']['avg_selection_time']:.2f}"])
        
        # Write agent distribution
        writer.writerow([])
        writer.writerow(["Agent Distribution", "Count (%)"])
        
        # List agent names
        for agent, count in results['standard']['agent_selection'].items():
            pct = (count / total_queries * 100) if total_queries > 0 else 0
            writer.writerow([agent, f"{count} ({pct:.1f}%)"])
    
    print(f"\nResults saved to {filename}")

if __name__ == "__main__":
    print("Starting benchmark...")
    results = run_benchmark(num_iterations=1)  # 1 iteration per query type for faster testing
    print_results(results)
    save_results_to_csv(results)