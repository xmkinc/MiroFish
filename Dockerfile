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

WORKDIR /app

# Copy backend source first
COPY backend/ ./backend/

# Install Python dependencies using pip directly into system Python
RUN pip install --no-cache-dir -e ./backend/

# Copy built frontend into frontend/dist folder
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

EXPOSE 5001

# Use system Python (packages installed via pip)
CMD ["python", "backend/run_prod.py"]
