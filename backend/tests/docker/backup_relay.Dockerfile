# Operator-built relay for restore sandboxes; never mount application volumes/secrets.
FROM python:3.12-alpine
COPY backend/app/modules/backups/relay.py /relay.py
USER 65534:65534
CMD ["python", "/relay.py"]
