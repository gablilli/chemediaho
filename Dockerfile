# Use the official Python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask app into the container
COPY . .

# Expose port 5000
EXPOSE 5000

# Command to run the app
CMD ["python", "app.py"]
