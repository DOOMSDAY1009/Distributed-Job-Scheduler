# Background Job Processing System

This project implements a mini distributed background processing system inspired by real-world queue-based platforms. It includes user registration, project and queue management, job submission, worker processing, retry handling, dead-letter behavior, and a monitoring dashboard.

## What is included
- Authentication basics
- Project and queue management
- Immediate, delayed, scheduled, and recurring job submission
- Worker registration and heartbeat handling
- Persistent SQLite storage
- Automatic background processing of pending jobs
- Retry and dead-letter handling
- Dashboard metrics for queue health and worker activity
- Automated tests and supporting documentation

## Run the backend

```powershell
cd C:\Users\ACER\background-job-system
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## Run the frontend

```powershell
cd C:\Users\ACER\background-job-system
python -m http.server 8080
```

Then open:
- http://127.0.0.1:8080

## API overview

- POST /auth/register
- POST /auth/login
- POST /projects
- GET /projects
- POST /queues
- GET /queues
- POST /jobs
- GET /jobs
- POST /workers
- GET /workers
- POST /workers/{worker_id}/heartbeat
- POST /jobs/process
- GET /dashboard

## Testing

```powershell
cd C:\Users\ACER\background-job-system\backend
pytest -q
```

## Notes

The implementation uses SQLite for persistence and a background worker loop to simulate a production-style job processing service for coursework and assignment purposes.
