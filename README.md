# Document Chat Application

This application allows users to upload documents and chat with AI models about the content of those documents. The application uses semantic search to find relevant content in documents to provide accurate responses.

## Features

- Document upload and processing (PDF, TXT)
- Chat with AI about document contents
- Semantic search for accurate document retrieval
- Model selection with adjustable parameters
- Code highlighting and markdown support

## Project Structure

The application consists of:

- **Backend**: Flask API that processes documents and connects to LLM services
- **Frontend**: React application that provides the user interface
- **LLM Service**: Integration with Ollama for language model capabilities

## Running with Docker (Recommended)

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/) (usually included with Docker Desktop)

### Steps to Run

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd arun-ai-lab
   ```

2. **Build and start the containers**
   ```bash
   docker-compose up -d
   ```
   *Note: Required Ollama models (text-embedding-bge-m3, deepseek-r1-distill-qwen-32b-mlx) will be automatically downloaded on first startup. This may take some time depending on your internet connection.*

3. **Access the application**
   - Frontend: [http://localhost:3000](http://localhost:3000)
   - Backend API: [http://localhost:5001/api](http://localhost:5001/api)

### Managing the Docker Application

- **Stop the application**
  ```bash
  docker-compose down
  ```

- **View logs**
  ```bash
  docker-compose logs
  docker-compose logs -f  # Follow logs in real-time
  ```

- **Rebuild after changes**
  ```bash
  docker-compose build
  docker-compose up -d
  ```

For more detailed Docker instructions, see [DOCKER_README.md](DOCKER_README.md).

## Running Locally (Alternative)

### Backend Setup

1. **Navigate to the backend directory**
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the server**
   ```bash
   python app.py
   ```
   The backend will be available at http://localhost:5001

### Frontend Setup

1. **Navigate to the frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start the development server**
   ```bash
   npm start
   ```
   The frontend will be available at http://localhost:3000

### LLM Service Setup

This application requires an Ollama service running locally:

1. **Install Ollama**
   Follow instructions at [Ollama.ai](https://ollama.ai/)

2. **Pull required models**
   ```bash
   ollama pull text-embedding-bge-m3
   ollama pull deepseek-r1-distill-qwen-32b-mlx
   ```

3. **Start Ollama**
   The service should be available at http://localhost:1234

## License

[MIT License](LICENSE)
