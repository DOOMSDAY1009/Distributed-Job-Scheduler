import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

os.environ['TESTING'] = '1'
sys.path.append(str(Path(__file__).resolve().parent))

from main import app, init_db

client = TestClient(app)


def test_health_check():
    init_db()
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_create_and_process_job():
    init_db()
    client.post('/auth/register', json={"username": "alice", "email": "alice@example.com", "password": "secret"})
    client.post('/projects', json={"name": "My Company"})
    client.post('/queues', json={"name": "email_queue", "concurrency": 2, "retries": 2})

    job_response = client.post('/jobs', json={
        "queue_name": "email_queue",
        "payload": {"to": "abc@gmail.com", "subject": "Welcome", "body": "Hello user"},
        "job_type": "immediate"
    })
    assert job_response.status_code == 200

    process_response = client.post('/jobs/process')
    assert process_response.status_code == 200
    assert process_response.json()['processed'] >= 1

    dashboard_response = client.get('/dashboard')
    assert dashboard_response.status_code == 200
    assert dashboard_response.json()['total_jobs'] >= 1


def test_dashboard_updates_queue_stats_after_processing():
    init_db()
    client.post('/queues', json={"name": "stats_queue", "concurrency": 2, "retries": 1})
    client.post('/jobs', json={
        "queue_name": "stats_queue",
        "payload": {"task": "test"},
        "job_type": "immediate"
    })

    process_response = client.post('/jobs/process')
    assert process_response.status_code == 200
    assert process_response.json()['processed'] == 1

    dashboard_response = client.get('/dashboard')
    data = dashboard_response.json()
    queue_stats = data['queue_sizes'][0]
    assert queue_stats['completed'] == 1
    assert queue_stats['pending'] == 0
