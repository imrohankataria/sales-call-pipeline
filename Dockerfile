FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir '.[aws]' && useradd --uid 10001 --create-home agent
USER agent
EXPOSE 8080
CMD ["python", "-m", "gtm_starter.app"]
