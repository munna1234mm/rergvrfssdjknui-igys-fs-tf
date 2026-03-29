# Use official Playwright Python image which includes all browser dependencies
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set work directory
WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Environment variable for port (Render uses this)
ENV PORT=10000

# Start services via app.py (Starts both Bot and Flask)
CMD ["python", "app.py"]
