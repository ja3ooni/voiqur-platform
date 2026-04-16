FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the WORKDIR to the root of the project
WORKDIR /project

# Set up virtual environment
ENV VIRTUAL_ENV=/project/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN uv venv $VIRTUAL_ENV

# 1. Copy the requirements from the backend folder
# We keep the 'backend' prefix so the pathing stays consistent
COPY backend/requirements.txt ./backend/
RUN uv pip install --no-cache-dir -r backend/requirements.txt

# 2. Copy the entire backend folder into the container
# This results in: /project/backend/app/main.py
COPY backend/ ./backend/

# 3. Set the PYTHONPATH so Python knows where to look for modules
ENV PYTHONPATH=/project/backend

# 4. Run uvicorn pointing to the correct nested path
# We stay in /project and point to backend.app.main
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]