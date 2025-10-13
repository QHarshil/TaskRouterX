"""
Task scheduling algorithms for TaskRouterX.

This module implements various scheduling strategies for assigning tasks to worker pools.
"""

import logging
from typing import Optional, List
from abc import ABC, abstractmethod

from store.models import Task, WorkerPool, AlgorithmType
from core.worker import worker_simulator

logger = logging.getLogger(__name__)


class SchedulingAlgorithm(ABC):
    """
    Abstract base class for scheduling algorithms.
    
    All scheduling algorithms must implement the select_worker method.
    """
    
    @abstractmethod
    def select_worker(self, task: Task, worker_pools: List[WorkerPool]) -> Optional[WorkerPool]:
        """
        Select the best worker pool for a given task.
        
        Args:
            task: Task to be scheduled
            worker_pools: Available worker pools
            
        Returns:
            Optional[WorkerPool]: Selected worker pool, or None if no suitable pool found
        """
        pass


class FIFOScheduler(SchedulingAlgorithm):
    """
    First-In-First-Out scheduling algorithm.
    
    Selects the first available worker pool in the preferred region.
    Simple and predictable, but doesn't optimize for cost or priority.
    """
    
    def select_worker(self, task: Task, worker_pools: List[WorkerPool]) -> Optional[WorkerPool]:
        """
        Select first available worker in the task's preferred region.
        
        Args:
            task: Task to be scheduled
            worker_pools: Available worker pools
            
        Returns:
            Optional[WorkerPool]: First available worker pool
        """
        # First, try to find a worker in the preferred region
        for pool in worker_pools:
            if pool.region == task.region and worker_simulator.can_accept_task(pool):
                logger.info(f"FIFO: Selected {pool.name} for task {task.id}")
                return pool
        
        # If no worker in preferred region, try any available worker
        for pool in worker_pools:
            if worker_simulator.can_accept_task(pool):
                logger.info(f"FIFO: Selected {pool.name} (fallback) for task {task.id}")
                return pool
                
        logger.warning(f"FIFO: No available worker for task {task.id}")
        return None


class PriorityScheduler(SchedulingAlgorithm):
    """
    Priority-based scheduling algorithm.
    
    Considers both task priority and worker availability.
    High-priority tasks get preference for better (faster/cheaper) workers.
    """
    
    def select_worker(self, task: Task, worker_pools: List[WorkerPool]) -> Optional[WorkerPool]:
        """
        Select worker based on task priority and worker characteristics.
        
        High-priority tasks get workers with lower cost and more capacity.
        
        Args:
            task: Task to be scheduled
            worker_pools: Available worker pools
            
        Returns:
            Optional[WorkerPool]: Best worker pool for the task's priority
        """
        # Filter available workers in preferred region
        available_pools = [
            pool for pool in worker_pools
            if pool.region == task.region and worker_simulator.can_accept_task(pool)
        ]
        
        # If no workers in preferred region, consider all regions
        if not available_pools:
            available_pools = [
                pool for pool in worker_pools
                if worker_simulator.can_accept_task(pool)
            ]
        
        if not available_pools:
            logger.warning(f"Priority: No available worker for task {task.id}")
            return None
        
        # For high-priority tasks (>= 7), prefer lower cost
        if task.priority >= 7:
            selected = min(available_pools, key=lambda p: p.cost_per_unit)
            logger.info(f"Priority: Selected low-cost {selected.name} for high-priority task {task.id}")
        # For medium-priority tasks (4-6), balance cost and availability
        elif task.priority >= 4:
            selected = min(available_pools, key=lambda p: (p.cost_per_unit, -p.capacity))
            logger.info(f"Priority: Selected balanced {selected.name} for medium-priority task {task.id}")
        # For low-priority tasks (<4), prefer available capacity
        else:
            selected = max(available_pools, key=lambda p: worker_simulator.get_available_capacity(p))
            logger.info(f"Priority: Selected high-capacity {selected.name} for low-priority task {task.id}")
        
        return selected


class MinCostScheduler(SchedulingAlgorithm):
    """
    Minimum cost scheduling algorithm.
    
    Always selects the cheapest available worker pool.
    Optimizes for cost efficiency over latency or priority.
    """
    
    def select_worker(self, task: Task, worker_pools: List[WorkerPool]) -> Optional[WorkerPool]:
        """
        Select the cheapest available worker pool.
        
        Args:
            task: Task to be scheduled
            worker_pools: Available worker pools
            
        Returns:
            Optional[WorkerPool]: Cheapest available worker pool
        """
        # Filter available workers
        available_pools = [
            pool for pool in worker_pools
            if worker_simulator.can_accept_task(pool)
        ]
        
        if not available_pools:
            logger.warning(f"MinCost: No available worker for task {task.id}")
            return None
        
        # Prefer workers in the same region to avoid cross-region costs
        region_pools = [p for p in available_pools if p.region == task.region]
        if region_pools:
            selected = min(region_pools, key=lambda p: p.cost_per_unit)
        else:
            selected = min(available_pools, key=lambda p: p.cost_per_unit)
        
        logger.info(f"MinCost: Selected {selected.name} (cost: ${selected.cost_per_unit}) for task {task.id}")
        return selected


class SchedulerFactory:
    """
    Factory for creating scheduling algorithm instances.
    
    Provides a centralized way to instantiate schedulers based on algorithm type.
    """
    
    _algorithms = {
        AlgorithmType.FIFO: FIFOScheduler,
        AlgorithmType.PRIORITY: PriorityScheduler,
        AlgorithmType.MIN_COST: MinCostScheduler,
    }
    
    @classmethod
    def create(cls, algorithm_type: AlgorithmType) -> SchedulingAlgorithm:
        """
        Create a scheduler instance for the given algorithm type.
        
        Args:
            algorithm_type: Type of scheduling algorithm
            
        Returns:
            SchedulingAlgorithm: Instance of the requested scheduler
            
        Raises:
            ValueError: If algorithm type is not supported
        """
        algorithm_class = cls._algorithms.get(algorithm_type)
        if not algorithm_class:
            raise ValueError(f"Unsupported algorithm type: {algorithm_type}")
        return algorithm_class()
    
    @classmethod
    def get_available_algorithms(cls) -> List[AlgorithmType]:
        """
        Get list of available algorithm types.
        
        Returns:
            List[AlgorithmType]: Available algorithm types
        """
        return list(cls._algorithms.keys())

