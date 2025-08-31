# Use lightweight Python image
FROM python:3.9-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies including Tesseract OCR
RUN apt-get update && apt-get install -y tesseract-ocr

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all app files into container
COPY . .

# Expose port 8501 for Streamlit
EXPOSE 8501

# Run the Streamlit app
ENTRYPOINT ["streamlit", "run"]
CMD ["app.py", "--server.port=8501", "--server.address=0.0.0.0"]
