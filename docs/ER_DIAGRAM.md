# ER Diagram

Entities:
- User
- Project
- Queue
- Job
- Worker

Relationships:
- User creates many Projects
- Project contains many Queues
- Queue contains many Jobs
- Worker processes many Jobs
