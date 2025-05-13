# AI-Powered QA Documentation Generator

This project automatically generates comprehensive QA documentation from website analysis using AI, providing a documentation-first approach for QA teams.

## Features

- **Website Crawling**: Automatically crawls target websites to identify and parse UI elements.
- **Test Case Generation**: Generates test cases covering functional, usability, and edge case scenarios.
- **Structured Output**: Produces documentation in both JSON and human-readable Markdown.
- **Batch Processing**: Handles multiple URLs with appropriate rate-limiting.
- **Authentication Support**: Handles basic HTTP and session token-based authentication.

## Requirements

- Python 3.9+
- MongoDB 6.0+
- Redis 6.0+
- OpenAI API key

## Installation

### Local Development

1. Clone the repository:
   ```
   git clone https://github.com/your-org/qa-doc-generator.git
   cd qa-doc-generator
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Install Playwright browsers:
   ```
   python -m playwright install
   ```

5. Create a `.env` file with your configuration (see `.env.example`).

### Docker Deployment

1. Create a `.env` file with your configuration.

2. Build and start the services:
   ```
   docker-compose up -d
   ```

## Usage

### Starting the API

```
python src/main.py
```

The API will be available at `http://localhost:8000`.

### API Endpoints

- `POST /jobs`: Create a new job to process URLs
- `GET /jobs/{job_id}`: Get job status
- `GET /jobs/{job_id}/results`: Get job results
- `GET /docs/{doc_id}/json`: Get JSON documentation
- `GET /docs/{doc_id}/markdown`: Get Markdown documentation
- `GET /health`: Health check endpoint

### Example Request

```python
import requests

response = requests.post(
    "http://localhost:8000/jobs",
    json={
        "urls": ["https://example.com/page-to-test"],
        "auth_config": {
            "auth_type": "basic",
            "username": "user",
            "password": "pass"
        },
        "rate_limit_requests_per_minute": 10
    }
)

job_id = response.json()["job_id"]
print(f"Job created with ID: {job_id}")
```

## Architecture

The system consists of the following components:

- **FastAPI Application**: Provides the REST API interface.
- **Celery Workers**: Handle background processing of jobs.
- **Playwright Crawler**: Analyzes websites and extracts UI elements.
- **LLM-based Analyzer**: Generates test cases using OpenAI's GPT model.
- **Document Generator**: Produces JSON and Markdown output.
- **MongoDB**: Stores job data and generated documentation.
- **Redis**: Manages the job queue and rate limiting.

## License

[MIT License](LICENSE) 