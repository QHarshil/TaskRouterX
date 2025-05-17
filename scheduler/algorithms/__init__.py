from abc import ABC, abstractmethod
from typing import Dict, List, Any
import logging
import networkx as nx
import numpy as np
from sklearn.linear_model import LinearRegression
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)

# Default algorithm
DEFAULT_ALGORITHM = os.getenv("DEFAULT_ALGORITHM", "fifo")


class SchedulingAlgorithm(ABC):
    """
    Abstract base class for scheduling algorithms.
    All scheduling algorithms must implement the route method.
    """
    
    @abstractmethod
    def route(self, tasks: List[Dict[str, Any]], worker_pools: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Route tasks to worker pools.
        
        Args:
            tasks: List of task dictionaries
            worker_pools: List of worker pool dictionaries
            
        Returns:
            Dict mapping task IDs to worker pool IDs
        """
        pass


class FIFOAlgorithm(SchedulingAlgorithm):
    """
    First-In-First-Out scheduling algorithm.
    Routes tasks to the first available worker pool in the preferred region.
    """
    
    def route(self, tasks: List[Dict[str, Any]], worker_pools: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Route tasks using FIFO algorithm.
        
        Args:
            tasks: List of task dictionaries
            worker_pools: List of worker pool dictionaries
            
        Returns:
            Dict mapping task IDs to worker pool IDs
        """
        assignments = {}
        
        # Group worker pools by region
        pools_by_region = {}
        for pool in worker_pools:
            region = pool["region"]
            if region not in pools_by_region:
                pools_by_region[region] = []
            pools_by_region[region].append(pool)
        
        # Process tasks in order
        for task in tasks:
            task_id = str(task["id"])
            preferred_region = task["region"]
            
            # Try preferred region first
            assigned = False
            if preferred_region in pools_by_region:
                for pool in pools_by_region[preferred_region]:
                    if pool["current_load"] < pool["capacity"]:
                        assignments[task_id] = str(pool["id"])
                        assigned = True
                        break
            
            # If no pool available in preferred region, try any region
            if not assigned:
                for region, pools in pools_by_region.items():
                    if assigned:
                        break
                    for pool in pools:
                        if pool["current_load"] < pool["capacity"]:
                            assignments[task_id] = str(pool["id"])
                            assigned = True
                            break
            
            # If still not assigned, queue for later
            if not assigned:
                logger.warning(f"Task {task_id} could not be assigned to any worker pool")
        
        return assignments


class GreedyAlgorithm(SchedulingAlgorithm):
    """
    Greedy scheduling algorithm.
    Routes tasks to minimize cost while respecting priority.
    """
    
    def route(self, tasks: List[Dict[str, Any]], worker_pools: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Route tasks using Greedy algorithm.
        
        Args:
            tasks: List of task dictionaries
            worker_pools: List of worker pool dictionaries
            
        Returns:
            Dict mapping task IDs to worker pool IDs
        """
        assignments = {}
        
        # Sort tasks by priority (highest first)
        sorted_tasks = sorted(tasks, key=lambda t: t["priority"], reverse=True)
        
        # Filter available worker pools
        available_pools = [p for p in worker_pools if p["current_load"] < p["capacity"]]
        
        # Process tasks in priority order
        for task in sorted_tasks:
            task_id = str(task["id"])
            preferred_region = task["region"]
            
            # Filter pools by region preference
            preferred_pools = [p for p in available_pools if p["region"] == preferred_region]
            
            # If no preferred pools available, use any available pool
            candidate_pools = preferred_pools if preferred_pools else available_pools
            
            if candidate_pools:
                # Sort pools by cost (lowest first)
                sorted_pools = sorted(candidate_pools, key=lambda p: p["cost_per_unit"])
                
                # Assign to lowest cost pool
                best_pool = sorted_pools[0]
                assignments[task_id] = str(best_pool["id"])
                
                # Update pool load
                best_pool["current_load"] += 1
                
                # Remove pool if now at capacity
                if best_pool["current_load"] >= best_pool["capacity"]:
                    available_pools.remove(best_pool)
            else:
                logger.warning(f"Task {task_id} could not be assigned to any worker pool")
        
        return assignments


class MinCostFlowAlgorithm(SchedulingAlgorithm):
    """
    Minimum Cost Flow scheduling algorithm.
    Uses network flow optimization to globally minimize cost.
    """
    
    def route(self, tasks: List[Dict[str, Any]], worker_pools: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Route tasks using Minimum Cost Flow algorithm.
        
        Args:
            tasks: List of task dictionaries
            worker_pools: List of worker pool dictionaries
            
        Returns:
            Dict mapping task IDs to worker pool IDs
        """
        if not tasks or not worker_pools:
            return {}
            
        # Create directed graph
        G = nx.DiGraph()
        
        # Add source and sink nodes
        G.add_node("source")
        G.add_node("sink")
        
        # Add task nodes and connect to source
        for task in tasks:
            task_id = str(task["id"])
            G.add_node(task_id)
            G.add_edge("source", task_id, capacity=1, weight=0)
        
        # Add worker pool nodes and connect to sink
        for pool in worker_pools:
            pool_id = str(pool["id"])
            G.add_node(pool_id)
            remaining_capacity = pool["capacity"] - pool["current_load"]
            if remaining_capacity > 0:
                G.add_edge(pool_id, "sink", capacity=remaining_capacity, weight=0)
        
        # Connect tasks to worker pools with costs
        for task in tasks:
            task_id = str(task["id"])
            task_priority = task["priority"]
            task_region = task["region"]
            
            for pool in worker_pools:
                pool_id = str(pool["id"])
                pool_region = pool["region"]
                pool_cost = pool["cost_per_unit"]
                
                # Calculate cost based on region match and pool cost
                region_penalty = 0 if pool_region == task_region else 10
                priority_factor = 11 - task_priority  # Invert priority (1-10) to make higher priority lower cost
                
                # Final cost is a combination of factors
                cost = (pool_cost * priority_factor) + region_penalty
                
                # Add edge with capacity 1 and calculated cost
                G.add_edge(task_id, pool_id, capacity=1, weight=cost)
        
        try:
            # Solve minimum cost flow problem
            flow_dict = nx.min_cost_flow(G)
            
            # Extract assignments from flow solution
            assignments = {}
            for task in tasks:
                task_id = str(task["id"])
                for pool in worker_pools:
                    pool_id = str(pool["id"])
                    if task_id in flow_dict and pool_id in flow_dict[task_id] and flow_dict[task_id][pool_id] > 0:
                        assignments[task_id] = pool_id
                        break
            
            return assignments
            
        except nx.NetworkXError as e:
            logger.error(f"Network flow optimization failed: {e}")
            # Fall back to greedy algorithm
            logger.info("Falling back to greedy algorithm")
            return GreedyAlgorithm().route(tasks, worker_pools)


class MLDrivenAlgorithm(SchedulingAlgorithm):
    """
    Machine Learning driven scheduling algorithm.
    Uses historical data to predict optimal assignments.
    """
    
    def __init__(self):
        self.model = None
        self.trained = False
    
    def train(self, historical_data):
        """
        Train the ML model on historical data.
        
        Args:
            historical_data: DataFrame with historical task assignments and outcomes
        """
        if historical_data.empty:
            logger.warning("No historical data available for training")
            return
            
        try:
            # Extract features
            X = historical_data[['priority', 'cost', 'region_encoded', 'worker_pool_encoded']]
            
            # Extract target (e.g., completion time)
            y = historical_data['completion_time']
            
            # Train a simple linear regression model
            self.model = LinearRegression()
            self.model.fit(X, y)
            
            self.trained = True
            logger.info("ML model trained successfully")
            
        except Exception as e:
            logger.error(f"Failed to train ML model: {e}")
            self.trained = False
    
    def route(self, tasks: List[Dict[str, Any]], worker_pools: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Route tasks using ML-driven algorithm.
        
        Args:
            tasks: List of task dictionaries
            worker_pools: List of worker pool dictionaries
            
        Returns:
            Dict mapping task IDs to worker pool IDs
        """
        # If model not trained, fall back to MinCostFlow
        if not self.trained or self.model is None:
            logger.warning("ML model not trained, falling back to MinCostFlow algorithm")
            return MinCostFlowAlgorithm().route(tasks, worker_pools)
        
        assignments = {}
        
        # Create region and worker pool encodings
        regions = list(set(p["region"] for p in worker_pools))
        region_to_idx = {region: i for i, region in enumerate(regions)}
        
        pool_ids = [str(p["id"]) for p in worker_pools]
        pool_to_idx = {pool_id: i for i, pool_id in enumerate(pool_ids)}
        
        # Process each task
        for task in tasks:
            task_id = str(task["id"])
            
            # Skip if no available pools
            available_pools = [p for p in worker_pools if p["current_load"] < p["capacity"]]
            if not available_pools:
                logger.warning(f"No available worker pools for task {task_id}")
                continue
            
            # Prepare prediction data for each potential worker pool
            predictions = []
            
            for pool in available_pools:
                pool_id = str(pool["id"])
                
                # Create feature vector
                features = np.array([
                    task["priority"],
                    task["cost"],
                    region_to_idx.get(task["region"], 0),
                    pool_to_idx.get(pool_id, 0)
                ]).reshape(1, -1)
                
                # Predict completion time
                try:
                    predicted_time = self.model.predict(features)[0]
                    predictions.append((pool_id, predicted_time))
                except Exception as e:
                    logger.error(f"Prediction failed for task {task_id} on pool {pool_id}: {e}")
            
            # Assign to pool with lowest predicted completion time
            if predictions:
                best_pool_id = min(predictions, key=lambda x: x[1])[0]
                assignments[task_id] = best_pool_id
                
                # Update pool load
                for pool in worker_pools:
                    if str(pool["id"]) == best_pool_id:
                        pool["current_load"] += 1
                        break
            else:
                logger.warning(f"Could not make predictions for task {task_id}")
        
        return assignments


# Algorithm factory
def get_algorithm(algorithm_name=None):
    """
    Get a scheduling algorithm instance by name.
    
    Args:
        algorithm_name: Name of the algorithm to use
        
    Returns:
        SchedulingAlgorithm: Instance of the requested algorithm
    """
    if algorithm_name is None:
        algorithm_name = DEFAULT_ALGORITHM
        
    algorithms = {
        "fifo": FIFOAlgorithm,
        "greedy": GreedyAlgorithm,
        "min_cost_flow": MinCostFlowAlgorithm,
        "ml_driven": MLDrivenAlgorithm
    }
    
    if algorithm_name not in algorithms:
        logger.warning(f"Unknown algorithm: {algorithm_name}, falling back to {DEFAULT_ALGORITHM}")
        algorithm_name = DEFAULT_ALGORITHM
        
    return algorithms[algorithm_name]()
