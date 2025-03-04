# Docker Setup for AI Lab

This project has been containerized using Docker to simplify deployment and ensure consistent execution across different environments.

## Prerequisites

- Docker: [Install Docker](https://docs.docker.com/get-docker/)
- Docker Compose: [Install Docker Compose](https://docs.docker.com/compose/install/) (Usually included with Docker Desktop)

## Components

The application consists of three main services:

1. **Backend**: A Flask API that processes documents and connects to the LLM service
2. **Frontend**: A React application that provides the user interface
3. **LLM Service**: An Ollama service that provides language model capabilities

## Getting Started

### Step 1: Clone the repository

```bash
git clone <repository-url>
cd arun-ai-lab
```

### Step 2: Build and start the containers

Run the following command to build and start all the containers:

```bash
docker-compose up -d
```

The first time you run this command, the Ollama service will automatically download the required models:
- text-embedding-bge-m3
- deepseek-r1-distill-qwen-32b-mlx

**Note:** The initial download of models may take several minutes depending on your internet connection. You can monitor the download progress by checking the logs:

```bash
docker-compose logs -f llm-service
```

### Step 3: Access the application

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:5001/api

## Managing the Application

### Stopping the application

```bash
docker-compose down
```

### Viewing logs

```bash
# View logs for all services
docker-compose logs

# View logs for a specific service
docker-compose logs backend
docker-compose logs frontend
docker-compose logs llm-service

# Follow logs in real-time
docker-compose logs -f
```

### Rebuilding after changes

If you make changes to the code, you need to rebuild the containers:

```bash
docker-compose build
docker-compose up -d
```

## Data Persistence

The application uses Docker volumes to persist data:

- `uploads`: Stores uploaded documents
- `documents`: Stores processed documents
- `ollama_models`: Stores the LLM models

## Troubleshooting

### LLM Service is not responding

The LLM service may take some time to download models on first use. Check the logs:

```bash
docker-compose logs llm-service
```

### Backend can't connect to LLM Service

Make sure the LLM service is running and accessible:

```bash
# Check if services are running
docker-compose ps

# Test connectivity from backend to LLM service
docker-compose exec backend ping llm-service
```

### Other Issues

Check the logs of the specific service that's having problems:

```bash
docker-compose logs <service-name>
```