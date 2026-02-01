<?php
/**
 * AI Team Dashboard - Single File PHP Implementation
 * No frameworks, no external libraries - Pure PHP + SQLite3
 */

// Database path (relative to memory/team/)
$dbPath = __DIR__ . '/../../memory/team/team.db';

// Initialize SQLite3 connection
$db = null;
$error = null;

try {
    if (!file_exists($dbPath)) {
        throw new Exception("Database not found: $dbPath");
    }
    $db = new SQLite3($dbPath, SQLITE3_OPEN_READONLY);
    $db->enableExceptions(true);
} catch (Exception $e) {
    $error = $e->getMessage();
}

// Helper function to fetch all rows from a query
function fetchAll($db, $sql) {
    if (!$db) return [];
    $result = $db->query($sql);
    $rows = [];
    while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
        $rows[] = $row;
    }
    return $rows;
}

// Helper function to fetch single row
function fetchOne($db, $sql) {
    if (!$db) return [];
    $result = $db->query($sql);
    return $result->fetchArray(SQLITE3_ASSOC) ?: [];
}

// Fetch all dashboard data
$stats = fetchOne($db, 'SELECT * FROM v_dashboard_stats');
$agents = fetchAll($db, 'SELECT * FROM v_agent_workload ORDER BY name');
$projects = fetchAll($db, 'SELECT * FROM v_project_status ORDER BY name');
$tasks = fetchAll($db, 'SELECT * FROM v_task_summary ORDER BY due_date, priority');
$activities = fetchAll($db, 'SELECT th.*, t.title as task_title, a.name as agent_name 
    FROM task_history th 
    LEFT JOIN tasks t ON th.task_id = t.id 
    LEFT JOIN agents a ON th.agent_id = a.id 
    ORDER BY th.timestamp DESC LIMIT 20');

// Format timestamp
$lastUpdated = date('Y-m-d H:i:s');

// Helper to get badge class
function badgeClass($status) {
    $map = [
        'idle' => 'badge-idle',
        'active' => 'badge-active',
        'blocked' => 'badge-blocked',
        'offline' => 'badge-offline',
        'todo' => 'badge-todo',
        'in_progress' => 'badge-in_progress',
        'done' => 'badge-done',
        'review' => 'badge-review',
        'cancelled' => 'badge-cancelled',
        'high' => 'badge-high',
        'normal' => 'badge-normal',
        'low' => 'badge-low',
        'critical' => 'badge-critical',
        'planning' => 'badge-planning',
    ];
    return $map[$status] ?? 'badge-idle';
}

// Stats configuration for display
$statConfig = [
    ['key' => 'total_agents', 'label' => 'Total Agents'],
    ['key' => 'active_agents', 'label' => 'Active'],
    ['key' => 'idle_agents', 'label' => 'Idle'],
    ['key' => 'blocked_agents', 'label' => 'Blocked'],
    ['key' => 'total_projects', 'label' => 'Total Projects'],
    ['key' => 'active_projects', 'label' => 'Active Projects'],
    ['key' => 'total_tasks', 'label' => 'Total Tasks'],
    ['key' => 'todo_tasks', 'label' => 'To Do'],
    ['key' => 'in_progress_tasks', 'label' => 'In Progress'],
    ['key' => 'completed_tasks', 'label' => 'Completed'],
    ['key' => 'blocked_tasks', 'label' => 'Blocked'],
];
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
    <title>AI Team Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eaeaea;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #00d9ff;
            margin-bottom: 10px;
            font-size: 2.5rem;
            text-shadow: 0 0 20px rgba(0, 217, 255, 0.5);
        }
        .last-updated {
            text-align: center;
            color: #888;
            margin-bottom: 30px;
            font-size: 0.9rem;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: #00d9ff;
        }
        .stat-label {
            color: #888;
            font-size: 0.85rem;
            margin-top: 5px;
        }
        .section {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .section h2 {
            color: #00d9ff;
            margin-bottom: 15px;
            font-size: 1.3rem;
            border-bottom: 1px solid rgba(0, 217, 255, 0.3);
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }
        th, td {
            padding: 12px 10px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        th {
            color: #00d9ff;
            font-weight: 600;
            background: rgba(0, 217, 255, 0.1);
        }
        tr:hover {
            background: rgba(255, 255, 255, 0.03);
        }
        .badge {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            display: inline-block;
        }
        .badge-idle { background: #4a5568; color: #fff; }
        .badge-active { background: #48bb78; color: #fff; }
        .badge-blocked { background: #f56565; color: #fff; }
        .badge-offline { background: #718096; color: #fff; }
        .badge-todo { background: #718096; color: #fff; }
        .badge-in_progress { background: #4299e1; color: #fff; }
        .badge-done { background: #48bb78; color: #fff; }
        .badge-review { background: #ed8936; color: #fff; }
        .badge-cancelled { background: #4a5568; color: #fff; }
        .badge-high { background: #f56565; color: #fff; }
        .badge-normal { background: #4299e1; color: #fff; }
        .badge-low { background: #48bb78; color: #fff; }
        .badge-critical { background: #9f7aea; color: #fff; }
        .badge-planning { background: #ed8936; color: #fff; }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d9ff, #0099cc);
            transition: width 0.3s;
        }
        .agent-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
        }
        .agent-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .agent-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .agent-name {
            font-weight: 600;
            color: #fff;
        }
        .agent-role {
            color: #888;
            font-size: 0.85rem;
        }
        .activity-item {
            padding: 10px;
            border-left: 3px solid #00d9ff;
            background: rgba(0, 217, 255, 0.05);
            margin-bottom: 10px;
            border-radius: 0 8px 8px 0;
        }
        .activity-time {
            color: #888;
            font-size: 0.8rem;
        }
        .two-columns {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .project-card {
            padding: 15px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 8px;
            margin-bottom: 10px;
        }
        .project-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .project-stats {
            font-size: 0.85rem;
            color: #888;
            margin-bottom: 10px;
        }
        .progress-text {
            text-align: center;
            font-size: 0.8rem;
            color: #888;
            margin-top: 5px;
        }
        .error {
            background: rgba(245, 101, 101, 0.2);
            border: 1px solid #f56565;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            color: #f56565;
        }
        .agent-stats {
            font-size: 0.85rem;
            color: #888;
        }
        @media (max-width: 900px) {
            .two-columns {
                grid-template-columns: 1fr;
            }
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            h1 {
                font-size: 1.8rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 AI Team Dashboard</h1>
        <p class="last-updated">Last updated: <?= htmlspecialchars($lastUpdated) ?> (auto-refreshes every 30s)</p>

        <?php if ($error): ?>
        <div class="error">
            <strong>Error:</strong> <?= htmlspecialchars($error) ?>
        </div>
        <?php else: ?>

        <!-- Stats Grid -->
        <div class="stats-grid">
            <?php foreach ($statConfig as $stat): ?>
                <?php $value = $stats[$stat['key']] ?? 0; ?>
                <div class="stat-card">
                    <div class="stat-value"><?= htmlspecialchars($value) ?></div>
                    <div class="stat-label"><?= htmlspecialchars($stat['label']) ?></div>
                </div>
            <?php endforeach; ?>
            <?php if (isset($stats['avg_progress'])): ?>
            <div class="stat-card">
                <div class="stat-value"><?= htmlspecialchars($stats['avg_progress'] ?? 0) ?>%</div>
                <div class="stat-label">Avg Progress</div>
            </div>
            <?php endif; ?>
            <?php if (isset($stats['due_today'])): ?>
            <div class="stat-card">
                <div class="stat-value"><?= htmlspecialchars($stats['due_today'] ?? 0) ?></div>
                <div class="stat-label">Due Today</div>
            </div>
            <?php endif; ?>
            <?php if (isset($stats['overdue_tasks'])): ?>
            <div class="stat-card">
                <div class="stat-value"><?= htmlspecialchars($stats['overdue_tasks'] ?? 0) ?></div>
                <div class="stat-label">Overdue</div>
            </div>
            <?php endif; ?>
        </div>

        <div class="two-columns">
            <!-- Agents Section -->
            <div class="section">
                <h2>👥 Agents (<?= count($agents) ?>)</h2>
                <div class="agent-grid">
                    <?php foreach ($agents as $agent): ?>
                    <div class="agent-card">
                        <div class="agent-header">
                            <div>
                                <div class="agent-name"><?= htmlspecialchars($agent['name'] ?? 'Unknown') ?></div>
                                <div class="agent-role"><?= htmlspecialchars($agent['role'] ?? 'N/A') ?></div>
                            </div>
                            <span class="badge <?= badgeClass($agent['status']) ?>"><?= htmlspecialchars($agent['status'] ?? 'idle') ?></span>
                        </div>
                        <div class="agent-stats">
                            Active Tasks: <?= htmlspecialchars($agent['active_tasks'] ?? 0) ?> | 
                            In Progress: <?= htmlspecialchars($agent['in_progress_tasks'] ?? 0) ?> |
                            Completed: <?= htmlspecialchars($agent['total_tasks_completed'] ?? 0) ?>
                        </div>
                    </div>
                    <?php endforeach; ?>
                </div>
            </div>

            <!-- Projects Section -->
            <div class="section">
                <h2>📊 Projects (<?= count($projects) ?>)</h2>
                <?php foreach ($projects as $project): ?>
                <div class="project-card">
                    <div class="project-header">
                        <strong><?= htmlspecialchars($project['name'] ?? 'Unnamed') ?></strong>
                        <span class="badge <?= badgeClass($project['status']) ?>"><?= htmlspecialchars($project['status'] ?? 'planning') ?></span>
                    </div>
                    <div class="project-stats">
                        Tasks: <?= htmlspecialchars($project['total_tasks'] ?? 0) ?> total | 
                        <?= htmlspecialchars($project['completed_tasks'] ?? 0) ?> done | 
                        <?= htmlspecialchars($project['in_progress_tasks'] ?? 0) ?> in progress | 
                        <?= htmlspecialchars($project['blocked_tasks'] ?? 0) ?> blocked
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: <?= htmlspecialchars($project['progress_pct'] ?? 0) ?>%"></div>
                    </div>
                    <div class="progress-text"><?= htmlspecialchars($project['progress_pct'] ?? 0) ?>% complete</div>
                </div>
                <?php endforeach; ?>
            </div>
        </div>

        <!-- Tasks Section -->
        <div class="section">
            <h2>📋 Tasks (<?= count($tasks) ?>)</h2>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Title</th>
                        <th>Project</th>
                        <th>Assignee</th>
                        <th>Status</th>
                        <th>Priority</th>
                        <th>Progress</th>
                        <th>Due Date</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($tasks as $task): ?>
                    <tr>
                        <td><?= htmlspecialchars($task['id'] ?? '-') ?></td>
                        <td><?= htmlspecialchars($task['title'] ?? 'Untitled') ?></td>
                        <td><?= htmlspecialchars($task['project_name'] ?? 'N/A') ?></td>
                        <td><?= htmlspecialchars($task['assignee_name'] ?? 'Unassigned') ?></td>
                        <td><span class="badge <?= badgeClass($task['status']) ?>"><?= htmlspecialchars($task['status'] ?? 'todo') ?></span></td>
                        <td><span class="badge <?= badgeClass($task['priority']) ?>"><?= htmlspecialchars($task['priority'] ?? 'normal') ?></span></td>
                        <td>
                            <div class="progress-bar" style="width: 60px; display: inline-block; vertical-align: middle; margin-right: 8px;">
                                <div class="progress-fill" style="width: <?= htmlspecialchars($task['progress'] ?? 0) ?>%"></div>
                            </div>
                            <?= htmlspecialchars($task['progress'] ?? 0) ?>%
                        </td>
                        <td><?= htmlspecialchars($task['due_date'] ?? 'N/A') ?></td>
                    </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>

        <!-- Activity Section -->
        <div class="section">
            <h2>📝 Recent Activity (<?= count($activities) ?> events)</h2>
            <?php foreach ($activities as $activity): ?>
            <div class="activity-item">
                <div style="display: flex; justify-content: space-between;">
                    <strong><?= strtoupper(htmlspecialchars($activity['action'] ?? 'unknown')) ?></strong>
                    <span class="activity-time"><?= htmlspecialchars($activity['timestamp'] ?? '-') ?></span>
                </div>
                <div style="margin-top: 5px;">
                    Task: <?= htmlspecialchars($activity['task_title'] ?? $activity['task_id'] ?? 'Unknown') ?><br>
                    Agent: <?= htmlspecialchars($activity['agent_name'] ?? 'System') ?>
                    <?php if ($activity['old_status'] && $activity['new_status']): ?>
                        | <?= htmlspecialchars($activity['old_status']) ?> → <?= htmlspecialchars($activity['new_status']) ?>
                    <?php endif; ?>
                    <?php if ($activity['old_progress'] !== null && $activity['new_progress'] !== null): ?>
                        | <?= htmlspecialchars($activity['old_progress']) ?>% → <?= htmlspecialchars($activity['new_progress']) ?>%
                    <?php endif; ?>
                    <?php if ($activity['notes']): ?>
                        <br><em><?= htmlspecialchars($activity['notes']) ?></em>
                    <?php endif; ?>
                </div>
            </div>
            <?php endforeach; ?>
        </div>

        <?php endif; // end if not error ?>
    </div>
</body>
</html>
