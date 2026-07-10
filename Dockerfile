FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml ./
COPY src ./src

RUN python -c "from pathlib import Path; Path('README.md').write_text('Safe Test Repair Harness container package\n', encoding='utf-8')"
RUN python -m pip install --no-cache-dir --upgrade pip
RUN python -m pip install --no-cache-dir .

CMD ["safe-repair", "demo", "guardrail"]
