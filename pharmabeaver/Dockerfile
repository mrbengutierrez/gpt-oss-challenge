FROM python:3.13-slim

WORKDIR /app

# Install deps first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy in the app code
COPY . .

# Create and seed the database at build time
RUN python -m app.seed

EXPOSE 5000

# Run Flask app
CMD ["python", "app/app.py"]
