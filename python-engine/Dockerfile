FROM python:3.12-slim
WORKDIR /app
COPY python-engine/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY database/imports/ /app/database/imports/
ENTRYPOINT ["python", "/app/database/imports/import_anvisa_medicines.py"]
