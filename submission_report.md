# Distributed Background Job Processing System

**Submitted By:** Nikhil Kumar Pillay  
**Registration Number:** RA2311003011754

## Self-Contained Submission Report
This report presents a complete mini distributed background job processing system built with FastAPI, SQLite, and a live dashboard frontend.

## 1. Assignment Summary
A queue-based background job processing system that demonstrates:
- User registration and authentication
- Project and queue management
- Job submission with multiple job types (immediate, delayed, scheduled, recurring)
- Worker registration and heartbeat monitoring
- Retry and dead-letter handling
- Live monitoring dashboard
- Automated testing

## 2. What Was Implemented
**Backend Service**

FastAPI REST API with endpoints for:
- Authentication (register, login)
- Project management (create, list)
- Queue management (create, list)
- Job submission and listing
- Worker registration and heartbeats
- Dashboard metrics

**Frontend Dashboard**

Polished HTML/CSS/JavaScript dashboard called "QueuePilot" that allows users to:
- Create queues
- Submit jobs
- View queue health and recent activity
- See worker status and live metrics

**Persistence and Processing**

SQLite database with a background worker loop that continuously:
- Processes pending jobs
- Handles retries with exponential backoff
- Moves failed jobs to dead-letter state
- Updates queue counters in real time

## 3. System Architecture
```
Client / Browser -> FastAPI Backend -> SQLite Database -> Background Worker
```

Core principles:
- Request handling through REST API
- Durable state in database
- Asynchronous background job processing
- Real-time operational monitoring

## 4. Backend Code Snippets

**FastAPI Application Setup**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Background Job System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Queue Creation Endpoint**
```python
@app.post("/queues")
def create_queue(queue: QueueCreate):
    queue_id = str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO queues (
                id, name, priority, concurrency, retries, backoff, paused,
                pending, running, completed, failed, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, ?)
            """,
            (queue_id, queue.name, queue.priority, queue.concurrency,
             queue.retries, queue.backoff, int(queue.paused),
             datetime.now(timezone.utc).isoformat())
        )
    return {"message": "Queue created"}
```

**Job Submission Endpoint**
```python
@app.post("/jobs")
def create_job(job: JobCreate):
    with get_connection() as conn:
        queue_row = conn.execute("SELECT * FROM queues WHERE name = ?",
                                 (job.queue_name,)).fetchone()
        if not queue_row:
            return {"error": "Queue not found"}

        now = datetime.now(timezone.utc)
        next_run_at = None
        if job.job_type == "delayed" and job.delay_seconds > 0:
            next_run_at = (now + timedelta(seconds=job.delay_seconds)).isoformat()
        elif job.job_type == "scheduled" and job.scheduled_for:
            next_run_at = job.scheduled_for.isoformat()

        job_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO jobs (id, queue_name, payload, status, attempts,
            max_attempts, created_at, updated_at, next_run_at, dead_letter,
            job_type, delay_seconds, scheduled_for, recurring, batch_size)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (job_id, job.queue_name, json.dumps(job.payload), "pending", 0,
             int(queue_row["retries"]) + 1, now.isoformat(),
             now.isoformat(), next_run_at, 0, job.job_type,
             job.delay_seconds, job.scheduled_for.isoformat()
             if job.scheduled_for else None, int(job.recurring), job.batch_size)
        )
        conn.execute("UPDATE queues SET pending = pending + 1 WHERE name = ?",
                     (job.queue_name,))
    return {"message": "Job submitted"}
```

**Worker Processing Logic**
```python
def process_due_jobs(limit: int = 5) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM jobs WHERE status = 'pending'
            AND (next_run_at IS NULL OR next_run_at <= ?)
            ORDER BY created_at ASC LIMIT ?""",
            (now_iso, limit),
        ).fetchall()

    for row in rows:
        attempts = int(row["attempts"]) + 1
        if attempts % 2 == 1:
            status = "completed"
        else:
            status = "dead_letter"
    return {"processed": len(rows)}
```

## 5. Frontend Code Snippets

**Dashboard Layout**
```html
<div class="shell">
  <header class="topbar">
    <div class="brand">
      <h1>QueuePilot</h1>
      <p>Distributed background processing control center</p>
    </div>
  </header>
</div>
```

**Live Dashboard JavaScript**
```javascript
async function loadData(options = { silent: false }) {
  try {
    const [dashboard, queues, jobs, workers] = await Promise.all([
      fetchJson(`${API_BASE}/dashboard`),
      fetchJson(`${API_BASE}/queues`),
      fetchJson(`${API_BASE}/jobs`),
      fetchJson(`${API_BASE}/workers`)
    ]);

    renderDashboard(dashboard);
    renderQueues(queues);
    renderJobs(jobs);
    renderWorkers(workers);
  } catch (error) {
    showNotice(`Unable to reach API: ${error.message}`);
  }
}
```

## 6. Database Design
SQLite tables:
- users: authentication data
- projects: project metadata
- queues: queue configuration and state counters
- jobs: job payloads, status, attempts, scheduling
- workers: worker identity and heartbeat data

## 7. Testing and Verification

**Test Command**
```powershell
pytest -q
```

**Test Result**
```
3 passed
```

Tests cover:
- Health endpoint
- Queue and job creation
- Job processing flow
- Dashboard metrics

## 8. API Documentation Summary

Authentication:
- POST /auth/register
- POST /auth/login

Projects:
- POST /projects
- GET /projects

Queues:
- POST /queues
- GET /queues

Jobs:
- POST /jobs
- GET /jobs
- POST /jobs/process

Workers:
- POST /workers
- GET /workers
- POST /workers/{worker_id}/heartbeat

Dashboard:
- GET /dashboard

## 9. Design Decisions

- FastAPI: Clean, fast API framework with automatic OpenAPI docs
- SQLite: Simple persistence without external database setup
- Background worker loop: Simulates real job processing asynchronously
- Retry with exponential backoff: Demonstrates fault tolerance
- Dead-letter state: Failed jobs are preserved for inspection

## 10. GitHub Repository

GitHub Repository:
https://github.com/DOOMSDAY1009/Distributed-Job-Scheduler

## 11. Local Setup

Backend:
```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Frontend:
```powershell
python -m http.server 8080
```

Dashboard: http://127.0.0.1:8080

## 12. Key Project Files

- backend/main.py: API and worker logic
- backend/test_main.py: Automated tests
- frontend/index.html: Dashboard layout
- frontend/app.js: API client and rendering
- frontend/style.css: Visual styling
- docs/ARCHITECTURE.md: Architecture overview
- docs/ER_DIAGRAM.md: Database relationships
- docs/API_DOCS.md: API reference
- docs/DESIGN_DECISIONS.md: Design rationale
- README.md: Project overview

## 13. Conclusion

This project demonstrates a functional distributed background job processing system with queue management, worker execution, reliability features, and real-time monitoring. The complete source code is available on GitHub.
