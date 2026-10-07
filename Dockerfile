# Use a minimal Python base image
FROM python:3.11-slim as builder

# Prevent Python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a non-root user and group
RUN groupadd -r kubediag && useradd -r -g kubediag kubediag

WORKDIR /app

# Copy only the files needed for installation to leverage Docker cache
COPY pyproject.toml README.md ./
COPY src/ src/

# Install the package globally in the container
RUN pip install --no-cache-dir .

# Change ownership of the app directory
RUN chown -R kubediag:kubediag /app

# Switch to the non-root user
USER kubediag

# The default command is the CLI entrypoint
ENTRYPOINT ["kubediag"]
CMD ["--help"]
