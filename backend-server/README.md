# The Betting Edge

The Betting Edge is a comprehensive platform designed to help users make informed betting decisions. It offers a variety of tools and data analysis features to enhance your betting experience. This repository contains the main server for HuskyHoldem, which provides APIs for authentication, user management, simulation jobs, leaderboard, and file uploads.

## Table of Contents
- [Introduction](#introduction)
- [Development](#development)
- [Architecture](#architecture)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)

## Introduction

The Betting Edge is a comprehensive platform designed to help users make informed betting decisions. It offers a variety of tools and data analysis features to enhance your betting experience. This server powers the core functionality of HuskyHoldem, such as signing up, running simulations, and managing user data.

## Development

### Manual Setup

1. **Prerequisites**:
   - PostgreSQL: Ensure a PostgreSQL instance is running. Update the connection settings in the application configuration.
   - Python 3.8+: Install Python on your system.

2. **Virtual Environment**:
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Server**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8002
   ```

### Docker Setup

1. **Prerequisites**:
   - Install Docker and Docker Compose on your system.

1. **Run with Docker**:
   ```bash
   docker-compose build
   ```
   ```bash
   docker-compose up
   ```
   This commands starts all services defined in `docker-compose.yml`, including the database, server, Redis, RabbitMQ, and three simulation workers.

## Architecture

The Betting Edge server uses a simple system with different parts working together. Here’s what we use:

- **FastAPI**: A tool to create fast and easy APIs in Python.
- **PostgreSQL**: A database to save user info, simulation results, and more.
- **Redis**: A fast storage for temporary data like caching.
- **RabbitMQ**: A tool to manage tasks like simulations, so they run smoothly.
- **Docker**: A containerization platform ensuring consistent environments across development and deployment.

### Components

- **Main Server**: Handles API requests for authentication, user management, simulation jobs, leaderboard updates, and file uploads. It interacts with PostgreSQL, Redis, and RabbitMQ.
- **Database (PostgreSQL)**: Stores all important data, like user profiles and leaderboard scores.
- **Redis**: Stores data temporarily to make things faster.
- **RabbitMQ**: Queues simulation jobs submitted by users and sends them to worker containers for processing.
- **Simulation Workers**: Three  containers (`worker_1`, `worker_2`, `worker_3`) that process simulation jobs in parallel from the RabbitMQ.

This system is easy to grow (e.g., add more workers) and works the same everywhere thanks to Docker.

## API Documentation

Once the server is running, access the interactive API documentation at `http://localhost:8002/docs` or visit `https://api.atcuw.org/docs` . This provides detailed endpoint information, request/response schemas, and a testing interface.

## Contributing

We welcome contributions from the community. To contribute, please follow these steps:

1. Fork the repository.
2. Create a new branch:
   ```bash
   git checkout -b feature-branch
   ```
3. Make your changes and commit them:
   ```bash
   git commit -m "Description of your changes"
   ```
4. Push to the branch:
   ```bash
   git push origin feature-branch
   ```
5. Create a pull request.

Please ensure your code follows the project's coding standards and includes tests where applicable.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.