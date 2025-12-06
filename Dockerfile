FROM python:3.12-slim
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
WORKDIR /app
COPY server.py index.html ./
RUN chown -R appuser:appgroup /app
USER appuser
EXPOSE 8003
CMD ["python", "server.py"]
