FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gamefydb/ ./gamefydb/
COPY run.py .

ENTRYPOINT ["python", "run.py"]
CMD ["--input", "excel", "--output", "output"]
