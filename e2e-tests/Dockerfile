# Image for the e2e-tests service in docker-compose.test.yml. Runs pytest
# against the live add-on + MariaDB + Mosquitto (network only — no docker
# socket, no shared volumes). Modeled on the fwc e2e-tests pattern.
FROM python:3.13-slim

WORKDIR /e2e
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY pytest.ini ./
COPY tests/ ./tests/

# Results land in the mounted /test-results volume (junit XML).
CMD ["pytest", "-v", "--junit-xml=/test-results/junit.xml"]
