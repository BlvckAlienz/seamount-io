# Stage 1: Build the application with all dependencies
FROM python:3.9-slim as builder

WORKDIR /app

# Install poetry for robust dependency management
RUN pip install poetry

# Copy only the files needed to install dependencies
COPY poetry.lock pyproject.toml ./

# Install dependencies into a virtual environment
RUN poetry install --no-root --no-dev

# Stage 2: Create the final, lean production image
FROM python:3.9-slim

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv /.venv

# Set the PATH to include the virtual environment's binaries
ENV PATH="/app/.venv/bin:$PATH"

# Copy the application source code
COPY . .

# Expose the port the application will run on
EXPOSE 8000

# The definitive command to run the production-grade gunicorn server
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000", "api.main:app"]