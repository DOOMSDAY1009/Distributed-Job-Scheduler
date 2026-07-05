import json
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Background Job System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")
WORKER_STOP_EVENT = threading.Event()
WORKER_THREAD: Optional[threading.Thread] = None


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class ProjectCreate(BaseModel):
    name: str


class QueueCreate(BaseModel):
    name: str
    priority: str = "high"
    concurrency: int = 5
    retries: int = 3
    backoff: str = "exponential"
    paused: bool = False


class JobCreate(BaseModel):
    queue_name: str
    payload: Dict[str, Any]
    job_type: str = "immediate"
    delay_seconds: int = 0
    scheduled_for: Optional[datetime] = None
    recurring: bool = False
    batch_size: int = 1


class Job(BaseModel):
    id: str
    queue_name: str
    payload: Dict[str, Any]
    status: str
    attempts: int
    max_attempts: int
    created_at: datetime
    updated_at: datetime
    next_run_at: Optional[datetime] = None
    dead_letter: bool = False


class WorkerStatus(BaseModel):
    id: str
    name: str
    online: bool
    last_heartbeat: datetime


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            DROP TABLE IF EXISTS workers;
            DROP TABLE IF EXISTS jobs;
            DROP TABLE IF EXISTS queues;
            DROP TABLE IF EXISTS projects;
            DROP TABLE IF EXISTS users;

            CREATE TABLE users (
                username TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                password TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE queues (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                priority TEXT NOT NULL,
                concurrency INTEGER NOT NULL,
                retries INTEGER NOT NULL,
                backoff TEXT NOT NULL,
                paused INTEGER NOT NULL,
                pending INTEGER NOT NULL,
                running INTEGER NOT NULL,
                completed INTEGER NOT NULL,
                failed INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE jobs (
                id TEXT PRIMARY KEY,
                queue_name TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL,
                max_attempts INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                next_run_at TEXT,
                dead_letter INTEGER NOT NULL,
                job_type TEXT NOT NULL,
                delay_seconds INTEGER NOT NULL,
                scheduled_for TEXT,
                recurring INTEGER NOT NULL,
                batch_size INTEGER NOT NULL
            );

            CREATE TABLE workers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                online INTEGER NOT NULL,
                last_heartbeat TEXT NOT NULL
            );
            """
        )


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value)


def serialize_job(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "queue_name": row["queue_name"],
        "payload": json.loads(row["payload"]),
        "status": row["status"],
        "attempts": row["attempts"],
        "max_attempts": row["max_attempts"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "next_run_at": row["next_run_at"],
        "dead_letter": bool(row["dead_letter"]),
    }


def serialize_worker(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "online": bool(row["online"]),
        "last_heartbeat": row["last_heartbeat"],
    }


def process_due_jobs(limit: int = 5) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    results = []

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM jobs
            WHERE status = 'pending'
              AND (next_run_at IS NULL OR next_run_at <= ?)
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (now_iso, limit),
        ).fetchall()

        for row in rows:
            queue_row = conn.execute(
                "SELECT * FROM queues WHERE name = ?",
                (row["queue_name"],),
            ).fetchone()
            if not queue_row:
                continue

            attempts = int(row["attempts"]) + 1
            next_run_at = None
            status = "running"
            updated_at = now.isoformat()
            dead_letter = 0

            conn.execute(
                "UPDATE queues SET pending = CASE WHEN pending > 0 THEN pending - 1 ELSE 0 END, running = running + 1 WHERE name = ?",
                (row["queue_name"],),
            )

            if attempts % 2 == 1:
                status = "completed"
                conn.execute(
                    "UPDATE queues SET running = running - 1, completed = completed + 1 WHERE name = ?",
                    (row["queue_name"],),
                )
            else:
                max_attempts = int(row["max_attempts"])
                if attempts >= max_attempts:
                    status = "dead_letter"
                    dead_letter = 1
                    conn.execute(
                        "UPDATE queues SET running = running - 1, failed = failed + 1 WHERE name = ?",
                        (row["queue_name"],),
                    )
                else:
                    status = "pending"
                    next_run_at = (now + timedelta(seconds=30 * attempts)).isoformat()
                    conn.execute(
                        "UPDATE queues SET running = running - 1 WHERE name = ?",
                        (row["queue_name"],),
                    )

            conn.execute(
                """
                UPDATE jobs
                SET status = ?, attempts = ?, updated_at = ?, next_run_at = ?, dead_letter = ?
                WHERE id = ?
                """,
                (status, attempts, updated_at, next_run_at, dead_letter, row["id"]),
            )
            results.append({"id": row["id"], "status": status})

    return {"processed": len(results), "results": results}


def worker_loop() -> None:
    while not WORKER_STOP_EVENT.is_set():
        process_due_jobs(limit=3)
        time.sleep(2)


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    if os.getenv("TESTING") == "1":
        return
    global WORKER_THREAD
    if WORKER_THREAD is None or not WORKER_THREAD.is_alive():
        WORKER_THREAD = threading.Thread(target=worker_loop, daemon=True)
        WORKER_THREAD.start()


@app.on_event("shutdown")
def shutdown_event() -> None:
    WORKER_STOP_EVENT.set()
    global WORKER_THREAD
    if WORKER_THREAD is not None:
        WORKER_THREAD.join(timeout=2)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register")
def register(user: UserCreate):
    with get_connection() as conn:
        existing = conn.execute("SELECT 1 FROM users WHERE username = ?", (user.username,)).fetchone()
        if existing:
            return {"error": "User already exists"}
        conn.execute(
            "INSERT INTO users (username, email, password, created_at) VALUES (?, ?, ?, ?)",
            (user.username, user.email, user.password, datetime.now(timezone.utc).isoformat()),
        )
    return {"message": "User registered", "username": user.username}


@app.post("/auth/login")
def login(user: UserLogin):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT username FROM users WHERE username = ? AND password = ?",
            (user.username, user.password),
        ).fetchone()
    if not row:
        return {"error": "Invalid credentials"}
    return {"message": "Login successful", "username": user.username}


@app.post("/projects")
def create_project(project: ProjectCreate):
    project_id = str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO projects (id, name, created_at) VALUES (?, ?, ?)",
            (project_id, project.name, datetime.now(timezone.utc).isoformat()),
        )
    return {"id": project_id, "name": project.name, "queues": []}


@app.get("/projects")
def list_projects():
    with get_connection() as conn:
        rows = conn.execute("SELECT id, name FROM projects ORDER BY created_at ASC").fetchall()
    return [{"id": row["id"], "name": row["name"], "queues": []} for row in rows]


@app.post("/queues")
def create_queue(queue: QueueCreate):
    queue_id = str(uuid.uuid4())
    with get_connection() as conn:
        existing = conn.execute("SELECT 1 FROM queues WHERE name = ?", (queue.name,)).fetchone()
        if existing:
            return {"error": "Queue already exists"}
        conn.execute(
            """
            INSERT INTO queues (
                id, name, priority, concurrency, retries, backoff, paused,
                pending, running, completed, failed, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, ?)
            """,
            (
                queue_id,
                queue.name,
                queue.priority,
                queue.concurrency,
                queue.retries,
                queue.backoff,
                int(queue.paused),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        row = conn.execute("SELECT * FROM queues WHERE id = ?", (queue_id,)).fetchone()
    return {
        "id": row["id"],
        "name": row["name"],
        "priority": row["priority"],
        "concurrency": row["concurrency"],
        "retries": row["retries"],
        "backoff": row["backoff"],
        "paused": bool(row["paused"]),
        "pending": row["pending"],
        "running": row["running"],
        "completed": row["completed"],
        "failed": row["failed"],
    }


@app.get("/queues")
def list_queues():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM queues ORDER BY created_at ASC").fetchall()
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "priority": row["priority"],
            "concurrency": row["concurrency"],
            "retries": row["retries"],
            "backoff": row["backoff"],
            "paused": bool(row["paused"]),
            "pending": row["pending"],
            "running": row["running"],
            "completed": row["completed"],
            "failed": row["failed"],
        }
        for row in rows
    ]


@app.post("/jobs")
def create_job(job: JobCreate):
    with get_connection() as conn:
        queue_row = conn.execute("SELECT * FROM queues WHERE name = ?", (job.queue_name,)).fetchone()
        if not queue_row:
            return {"error": "Queue not found"}

        now = datetime.now(timezone.utc)
        next_run_at = None
        if job.job_type == "delayed" and job.delay_seconds > 0:
            next_run_at = (now + timedelta(seconds=job.delay_seconds)).isoformat()
        elif job.job_type == "scheduled" and job.scheduled_for:
            next_run_at = job.scheduled_for.isoformat()
        elif job.job_type == "recurring":
            next_run_at = (now + timedelta(seconds=30)).isoformat()

        job_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO jobs (
                id, queue_name, payload, status, attempts, max_attempts, created_at,
                updated_at, next_run_at, dead_letter, job_type, delay_seconds,
                scheduled_for, recurring, batch_size
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                job.queue_name,
                json.dumps(job.payload),
                "pending",
                0,
                int(queue_row["retries"]) + 1,
                now.isoformat(),
                now.isoformat(),
                next_run_at,
                0,
                job.job_type,
                job.delay_seconds,
                job.scheduled_for.isoformat() if job.scheduled_for else None,
                int(job.recurring),
                job.batch_size,
            ),
        )
        conn.execute("UPDATE queues SET pending = pending + 1 WHERE name = ?", (job.queue_name,))
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

    return serialize_job(row)


@app.get("/jobs")
def list_jobs():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at ASC").fetchall()
    return [serialize_job(row) for row in rows]


@app.post("/workers")
def register_worker():
    worker_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO workers (id, name, online, last_heartbeat) VALUES (?, ?, ?, ?)",
            (worker_id, f"worker-{worker_id[:6]}", 1, now),
        )
    return {"id": worker_id, "name": f"worker-{worker_id[:6]}", "online": True, "last_heartbeat": now}


@app.get("/workers")
def list_workers():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM workers ORDER BY last_heartbeat DESC").fetchall()
    return [serialize_worker(row) for row in rows]


@app.post("/workers/{worker_id}/heartbeat")
def heartbeat(worker_id: str):
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM workers WHERE id = ?", (worker_id,)).fetchone()
        if not row:
            return {"error": "Worker not found"}
        conn.execute("UPDATE workers SET last_heartbeat = ?, online = 1 WHERE id = ?", (now, worker_id))
    return {"ok": True}


@app.post("/jobs/process")
def process_jobs():
    return process_due_jobs(limit=5)


@app.get("/dashboard")
def dashboard():
    with get_connection() as conn:
        queues = conn.execute("SELECT * FROM queues ORDER BY created_at ASC").fetchall()
        jobs = conn.execute("SELECT * FROM jobs").fetchall()
        workers = conn.execute("SELECT * FROM workers WHERE online = 1").fetchall()

    queue_stats = [
        {
            "name": queue["name"],
            "pending": queue["pending"],
            "running": queue["running"],
            "completed": queue["completed"],
            "failed": queue["failed"],
            "workers_online": len(workers),
        }
        for queue in queues
    ]

    return {
        "total_jobs": len(jobs),
        "failed_jobs": sum(1 for job in jobs if job["status"] == "dead_letter"),
        "running_jobs": sum(1 for job in jobs if job["status"] == "running"),
        "online_workers": len(workers),
        "queue_sizes": queue_stats,
        "throughput": sum(1 for job in jobs if job["status"] == "completed"),
    }
