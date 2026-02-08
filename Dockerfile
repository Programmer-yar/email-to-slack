# Build and run email-to-slack on Cloud Run Jobs (GCP)
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Application code
COPY email_to_slack/ ./email_to_slack/
COPY main.py ./

# Run one poll cycle (Cloud Scheduler will invoke this job every 5 minutes)
CMD ["python", "main.py"]
