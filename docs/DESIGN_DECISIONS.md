# Design Decisions

- FastAPI was chosen because it provides a clean API layer and quick development for assignment-style services.
- In-memory storage was used to keep the prototype simple and easy to run without a database.
- Retries are handled by scheduling jobs with an exponential-style delay based on the attempt count.
- Dead-lettering occurs once the maximum retry count is exceeded.
