# Architecture Diagram

The system follows a modular architecture:

1. Frontend sends requests to the API layer.
2. FastAPI backend handles authentication, project/queue/job management, and worker registration.
3. In-memory store holds users, projects, queues, jobs, and workers for the assignment scope.
4. A processing endpoint simulates worker execution with retry and dead-letter handling.
