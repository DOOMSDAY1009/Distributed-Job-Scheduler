# Worker Flow

The worker service runs as a background thread that periodically checks for pending jobs.

1. Read pending jobs from the database.
2. Select eligible jobs whose scheduled time has arrived.
3. Mark the job as running.
4. Process the job and update the queue counters.
5. If successful, mark the job as completed.
6. If failed, retry based on the configured retry policy.
7. If retries are exhausted, move the job to the dead-letter state.
