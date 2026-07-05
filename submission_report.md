# Distributed Background Job Processing System

## 1. Introduction
This project implements a mini distributed background processing system similar in concept to modern queue-based job platforms. It supports user registration and login, project management, queue management, job submission, background worker processing, retry handling, dead-letter processing, and a monitoring dashboard.

## 2. Objective
The main objective of this assignment was to design and implement a system where jobs are submitted to queues, workers process them, failures are retried, and the overall state is visible through a dashboard.

## 3. Features Implemented
### Authentication
- User registration
- User login

### Project Management
- Create projects
- Organize queues under projects

### Queue Management
- Create new queues
- Configure concurrency, retries, backoff, and paused state

### Job APIs
- Immediate jobs
- Delayed jobs
- Scheduled jobs
- Recurring jobs

### Worker Service
- Worker registration
- Heartbeat updates
- Continuous background processing of pending jobs

### Reliability Features
- Retry logic for failed jobs
- Dead-letter handling after repeated failures
- Queue state tracking for pending, running, completed, and failed jobs

### Monitoring Dashboard
- Total jobs
- Failed jobs
- Running jobs
- Online workers
- Queue sizes and throughput

## 4. Technology Stack
- Backend: FastAPI
- Frontend: HTML, CSS, JavaScript
- Database: SQLite
- Testing: Pytest

## 5. Architecture Overview
The application follows a simple layered architecture:
1. Frontend sends requests to the FastAPI backend.
2. The backend handles authentication, queue, job, and worker operations.
3. Jobs are stored in SQLite and processed by a background worker loop.
4. The dashboard reads the current system state and displays it to the user.

## 6. Database Design
The system uses SQLite with the following tables:
- users
- projects
- queues
- jobs
- workers

### Relationship Summary
- One user can create many projects.
- A project can contain many queues.
- A queue can contain many jobs.
- Workers process jobs from queues.

## 7. API Endpoints
### Authentication
- POST /auth/register
- POST /auth/login

### Projects
- POST /projects
- GET /projects

### Queues
- POST /queues
- GET /queues

### Jobs
- POST /jobs
- GET /jobs
- POST /jobs/process

### Workers
- POST /workers
- GET /workers
- POST /workers/{worker_id}/heartbeat

### Dashboard
- GET /dashboard

## 8. Frontend Description
The frontend provides a modern dashboard-style interface where users can:
- create queues
- submit jobs
- view queue metrics
- see recent jobs and workers
- refresh the live view

## 9. Testing
The project includes automated tests for the main functionality.

### Test Command
```powershell
pytest -q
```

### Result
```text
3 passed
```

## 10. How to Run
### Backend
```powershell
cd C:\Users\ACER\background-job-system
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Frontend
```powershell
cd C:\Users\ACER\background-job-system
python -m http.server 8080
```

## 11. Conclusion
This project successfully implements a functional mini version of a distributed background job processing system. It covers the main learning objectives of the assignment, including queue management, worker-based processing, retries, dead-letter handling, monitoring, documentation, and testing.
