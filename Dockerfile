# ============================================================
# Stage 1: Build frontend
# ============================================================
FROM node:20-slim AS frontend-builder

WORKDIR /app

# Install frontend dependencies
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN cd frontend && npm ci

# Copy frontend source and build
COPY frontend/ ./frontend/
RUN cd frontend && npm run build

# ============================================================
# Stage 2: Production image (Python backend + built frontend)
# ============================================================
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

# Install Python dependencies using uv into the system Python
# (not a virtualenv, so regular python can find them)
COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN cd backend && uv sync --frozen --no-dev --system

# Copy backend source
COPY backend/ ./backend/

# Copy built frontend into frontend/dist folder
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

EXPOSE 5001

# Run with system Python (packages installed to system via --system flag)
CMD ["python", "backend/run_prod.py"]
