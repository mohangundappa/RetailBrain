"""
Benchmark the optimized agent selection against the original approach.
This script measures the performance improvements and API call reduction.
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
ORIGINAL_CHAT_URL = f"{BASE_URL}/chat"
OPTIMIZED_CHAT_URL = f"{BASE_URL}/optimized/chat"

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
    Run a benchmark comparing original and optimized routes.
    
    Args:
        num_iterations: Number of iterations per query type
        
    Returns:
        Dictionary with benchmark results
    """
    results = {
        "original": {
            "total_time": 0,
            "total_queries": 0,
            "api_calls": 0,
            "agent_selection": {}
        },
        "optimized": {
            "total_time": 0,
            "total_queries": 0,
            "api_calls": 0,
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
    
    # Run original route tests
    print("\nTesting original route...")
    for i, (intent, query) in enumerate(test_queries):
        session_id = str(uuid.uuid4())
        print(f"  Query {i+1}/{len(test_queries)}: {query[:30]}...")
        
        start_time = time.time()
        response = requests.post(
            ORIGINAL_CHAT_URL,
            json={"message": query, "session_id": session_id}
        )
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            agent = result.get("agent_name", "unknown")
            
            # Update results
            results["original"]["total_time"] += elapsed
            results["original"]["total_queries"] += 1
            
            # Track agent selection
            if agent not in results["original"]["agent_selection"]:
                results["original"]["agent_selection"][agent] = 0
            results["original"]["agent_selection"][agent] += 1
    
    # Run optimized route tests
    print("\nTesting optimized route...")
    for i, (intent, query) in enumerate(test_queries):
        session_id = str(uuid.uuid4())
        print(f"  Query {i+1}/{len(test_queries)}: {query[:30]}...")
        
        start_time = time.time()
        response = requests.post(
            OPTIMIZED_CHAT_URL,
            json={"message": query, "session_id": session_id}
        )
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            agent = result.get("agent", "unknown")
            metadata = result.get("metadata", {})
            selection_time = metadata.get("selection_time", 0) if metadata else 0
            
            # Update results
            results["optimized"]["total_time"] += elapsed
            results["optimized"]["total_queries"] += 1
            results["optimized"]["selection_time"] += selection_time
            
            # Track agent selection
            if agent not in results["optimized"]["agent_selection"]:
                results["optimized"]["agent_selection"][agent] = 0
            results["optimized"]["agent_selection"][agent] += 1
    
    # Calculate averages
    if results["original"]["total_queries"] > 0:
        results["original"]["avg_time"] = results["original"]["total_time"] / results["original"]["total_queries"]
    
    if results["optimized"]["total_queries"] > 0:
        results["optimized"]["avg_time"] = results["optimized"]["total_time"] / results["optimized"]["total_queries"]
        results["optimized"]["avg_selection_time"] = results["optimized"]["selection_time"] / results["optimized"]["total_queries"]
    
    return results

def print_results(results):
    """Print the benchmark results in a readable format."""
    print("\n=== Benchmark Results ===")
    
    # Original route results
    print("\nOriginal Route:")
    print(f"  Total queries: {results['original']['total_queries']}")
    print(f"  Total time: {results['original']['total_time']:.2f} seconds")
    if 'avg_time' in results['original']:
        print(f"  Average time per query: {results['original']['avg_time']:.2f} seconds")
    
    print("  Agent selection distribution:")
    for agent, count in results['original']['agent_selection'].items():
        percentage = (count / results['original']['total_queries']) * 100
        print(f"    {agent}: {count} ({percentage:.1f}%)")
    
    # Optimized route results
    print("\nOptimized Route:")
    print(f"  Total queries: {results['optimized']['total_queries']}")
    print(f"  Total time: {results['optimized']['total_time']:.2f} seconds")
    if 'avg_time' in results['optimized']:
        print(f"  Average time per query: {results['optimized']['avg_time']:.2f} seconds")
    if 'avg_selection_time' in results['optimized']:
        print(f"  Average selection time: {results['optimized']['avg_selection_time']:.2f} seconds")
    
    print("  Agent selection distribution:")
    for agent, count in results['optimized']['agent_selection'].items():
        percentage = (count / results['optimized']['total_queries']) * 100
        print(f"    {agent}: {count} ({percentage:.1f}%)")
    
    # Performance comparison
    if 'avg_time' in results['original'] and 'avg_time' in results['optimized']:
        improvement = ((results['original']['avg_time'] - results['optimized']['avg_time']) / 
                       results['original']['avg_time']) * 100
        print(f"\nPerformance improvement: {improvement:.1f}%")

def save_results_to_csv(results):
    """Save benchmark results to a CSV file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"benchmark_results_{timestamp}.csv"
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(["Metric", "Original", "Optimized", "Improvement (%)"])
        
        # Write data
        total_queries_orig = results['original']['total_queries']
        total_queries_opt = results['optimized']['total_queries']
        writer.writerow(["Total Queries", total_queries_orig, total_queries_opt, "N/A"])
        
        total_time_orig = results['original']['total_time']
        total_time_opt = results['optimized']['total_time']
        time_improvement = ((total_time_orig - total_time_opt) / total_time_orig * 100) if total_time_orig > 0 else "N/A"
        writer.writerow(["Total Time (s)", f"{total_time_orig:.2f}", f"{total_time_opt:.2f}", f"{time_improvement:.1f}%"])
        
        if 'avg_time' in results['original'] and 'avg_time' in results['optimized']:
            avg_time_orig = results['original']['avg_time']
            avg_time_opt = results['optimized']['avg_time']
            avg_improvement = ((avg_time_orig - avg_time_opt) / avg_time_orig * 100) if avg_time_orig > 0 else "N/A"
            writer.writerow(["Avg Time Per Query (s)", f"{avg_time_orig:.2f}", f"{avg_time_opt:.2f}", f"{avg_improvement:.1f}%"])
        
        if 'avg_selection_time' in results['optimized']:
            writer.writerow(["Avg Selection Time (s)", "N/A", f"{results['optimized']['avg_selection_time']:.2f}", "N/A"])
        
        # Write agent distribution
        writer.writerow([])
        writer.writerow(["Agent Distribution", "Original Count (%)", "Optimized Count (%)"])
        
        # Combine all agent names
        all_agents = set(list(results['original']['agent_selection'].keys()) + 
                         list(results['optimized']['agent_selection'].keys()))
        
        for agent in all_agents:
            orig_count = results['original']['agent_selection'].get(agent, 0)
            opt_count = results['optimized']['agent_selection'].get(agent, 0)
            
            orig_pct = (orig_count / total_queries_orig * 100) if total_queries_orig > 0 else 0
            opt_pct = (opt_count / total_queries_opt * 100) if total_queries_opt > 0 else 0
            
            writer.writerow([agent, f"{orig_count} ({orig_pct:.1f}%)", f"{opt_count} ({opt_pct:.1f}%)"])
    
    print(f"\nResults saved to {filename}")

if __name__ == "__main__":
    print("Starting benchmark...")
    results = run_benchmark(num_iterations=3)  # 3 iterations per query type
    print_results(results)
    save_results_to_csv(results)