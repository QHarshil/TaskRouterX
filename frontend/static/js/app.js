// TaskRouterX Frontend Application

const API_BASE_URL = 'http://localhost:8000/api/v1';

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('TaskRouterX Dashboard Initialized');
    loadStats();
    loadWorkers();
    loadTasks();
    
    // Auto-refresh every 5 seconds
    setInterval(() => {
        loadStats();
        loadWorkers();
        loadTasks();
    }, 5000);
});

// Submit a new task
async function submitTask() {
    const taskType = document.getElementById('task-type').value;
    const priority = parseInt(document.getElementById('task-priority').value);
    const cost = parseFloat(document.getElementById('task-cost').value);
    const region = document.getElementById('task-region').value;
    
    const taskData = {
        type: taskType,
        priority: priority,
        cost: cost,
        region: region,
        metadata: {
            submitted_from: 'dashboard',
            timestamp: new Date().toISOString()
        }
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}/tasks`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(taskData)
        });
        
        if (response.ok) {
            const result = await response.json();
            showResult('task-result', `✅ Task created successfully!\nTask ID: ${result.id}\nStatus: ${result.status}`, 'success');
            
            // Refresh displays
            setTimeout(() => {
                loadStats();
                loadTasks();
            }, 500);
        } else {
            const error = await response.json();
            showResult('task-result', `❌ Error: ${error.detail || 'Failed to create task'}`, 'error');
        }
    } catch (error) {
        showResult('task-result', `❌ Network error: ${error.message}`, 'error');
    }
}

// Load system statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/system/stats`);
        if (response.ok) {
            const stats = await response.json();
            
            document.getElementById('stat-processed').textContent = stats.tasks_processed;
            document.getElementById('stat-pending').textContent = stats.tasks_pending;
            document.getElementById('stat-completed').textContent = stats.tasks_completed;
            document.getElementById('stat-failed').textContent = stats.tasks_failed;
            document.getElementById('stat-latency').textContent = `${(stats.average_latency * 1000).toFixed(0)}ms`;
            document.getElementById('stat-queue').textContent = stats.queue_size;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load worker pools
async function loadWorkers() {
    try {
        const response = await fetch(`${API_BASE_URL}/workers`);
        if (response.ok) {
            const data = await response.json();
            const workersContainer = document.getElementById('worker-pools');
            
            if (data.worker_pools.length === 0) {
                workersContainer.innerHTML = '<div class="loading">No worker pools available</div>';
                return;
            }
            
            workersContainer.innerHTML = data.worker_pools.map(pool => {
                const utilization = (pool.current_load / pool.capacity) * 100;
                const utilizationClass = utilization > 80 ? 'high' : '';
                
                return `
                    <div class="worker-card">
                        <div class="worker-name">${pool.name}</div>
                        <div class="worker-info">Region: ${pool.region}</div>
                        <div class="worker-info">Type: ${pool.resource_type.toUpperCase()}</div>
                        <div class="worker-info">Cost: $${pool.cost_per_unit}/unit</div>
                        <div class="worker-load">
                            <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #6c757d;">
                                <span>Load: ${pool.current_load}/${pool.capacity}</span>
                                <span>${utilization.toFixed(0)}%</span>
                            </div>
                            <div class="load-bar">
                                <div class="load-fill ${utilizationClass}" style="width: ${utilization}%"></div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
    } catch (error) {
        console.error('Error loading workers:', error);
        document.getElementById('worker-pools').innerHTML = '<div class="loading">Error loading worker pools</div>';
    }
}

// Load recent tasks
async function loadTasks() {
    try {
        const response = await fetch(`${API_BASE_URL}/tasks?page=1&page_size=10`);
        if (response.ok) {
            const data = await response.json();
            const tasksContainer = document.getElementById('recent-tasks');
            
            if (data.tasks.length === 0) {
                tasksContainer.innerHTML = '<div class="loading">No tasks yet. Submit a task to get started!</div>';
                return;
            }
            
            tasksContainer.innerHTML = data.tasks.map(task => {
                const statusClass = `status-${task.status}`;
                const taskIdShort = task.id.substring(0, 8);
                
                return `
                    <div class="task-item">
                        <div class="task-header">
                            <span class="task-id">${taskIdShort}...</span>
                            <span class="task-status ${statusClass}">${task.status}</span>
                        </div>
                        <div class="task-details">
                            Type: ${task.type} | Priority: ${task.priority} | Region: ${task.region}
                            ${task.worker_id ? `<br>Worker: ${task.worker_id}` : ''}
                            ${task.algorithm_used ? `| Algorithm: ${task.algorithm_used}` : ''}
                        </div>
                    </div>
                `;
            }).join('');
        }
    } catch (error) {
        console.error('Error loading tasks:', error);
        document.getElementById('recent-tasks').innerHTML = '<div class="loading">Error loading tasks</div>';
    }
}

// Switch scheduling algorithm
async function switchAlgorithm() {
    const algorithm = document.getElementById('algorithm-select').value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/algorithms/switch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ algorithm: algorithm })
        });
        
        if (response.ok) {
            const result = await response.json();
            showResult('algorithm-result', `✅ Algorithm switched to: ${result.algorithm.toUpperCase()}`, 'success');
        } else {
            const error = await response.json();
            showResult('algorithm-result', `❌ Error: ${error.detail || 'Failed to switch algorithm'}`, 'error');
        }
    } catch (error) {
        showResult('algorithm-result', `❌ Network error: ${error.message}`, 'error');
    }
}

// Run traffic simulation
async function runSimulation() {
    const taskCount = parseInt(document.getElementById('sim-count').value);
    const distribution = document.getElementById('sim-distribution').value;
    
    const simulationData = {
        task_count: taskCount,
        distribution: distribution,
        priority_range: [1, 10],
        cost_range: [0.1, 10.0]
    };
    
    try {
        showResult('simulation-result', `⏳ Starting simulation with ${taskCount} tasks...`, 'info');
        
        const response = await fetch(`${API_BASE_URL}/simulate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(simulationData)
        });
        
        if (response.ok) {
            const result = await response.json();
            showResult('simulation-result', 
                `✅ Simulation started!\nSimulation ID: ${result.id}\nTasks: ${result.task_count}\nStatus: ${result.status}`, 
                'success');
            
            // Refresh displays after a short delay
            setTimeout(() => {
                loadStats();
                loadTasks();
            }, 1000);
        } else {
            const error = await response.json();
            showResult('simulation-result', `❌ Error: ${error.detail || 'Failed to start simulation'}`, 'error');
        }
    } catch (error) {
        showResult('simulation-result', `❌ Network error: ${error.message}`, 'error');
    }
}

// Helper function to show results
function showResult(elementId, message, type) {
    const resultElement = document.getElementById(elementId);
    resultElement.textContent = message;
    resultElement.className = `result-section result-${type} show`;
    
    // Auto-hide after 5 seconds for success messages
    if (type === 'success') {
        setTimeout(() => {
            resultElement.classList.remove('show');
        }, 5000);
    }
}

// Helper function to format dates
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

