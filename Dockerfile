# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any necessary dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Initialize the database and apply migrations
RUN flask db init && \
    flask db migrate -m "Initial migration" && \
    flask db upgrade

# Expose the port the app runs on
EXPOSE 8000

# Define environment variable (optional)
ENV FLASK_ENV=development

# Run app.py when the container launches
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]
