# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy only the requirements file first to leverage Docker's caching
COPY requirements.txt /app

RUN mkdir -p /app/output

# Install common dependencies and Python dependencies in one step
RUN pip install --no-cache-dir -r requirements.txt

# Create .dockerignore file to exclude tests and test_scripts directories
RUN echo "tests/" > .dockerignore

# Copy the rest of the application files
COPY . /app/

# Define the default command to keep the container running
CMD ["tail", "-f", "/dev/null"]