#!/bin/bash
set -e

PROJECT_DIR="$HOME/Documents/project/OllamaAgent"
VENV_DIR="$HOME/Documents/py"
CONTAINER_NAME="agent_app"
MAX_WAIT=180

cd "$PROJECT_DIR"

echo "Starting Docker containers..."
docker compose up -d

echo "Waiting for agent_app to become healthy..."
elapsed=0
while true; do
  status=$(docker inspect -f '{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "starting")

  if [ "$status" == "healthy" ]; then
    break
  fi

  if [ "$status" == "unhealthy" ]; then
    echo "Container reported unhealthy. Check logs:"
    echo "  docker compose logs app"
    echo "  docker compose logs server"
    notify-send "OllamaAgent" "Failed to start: container unhealthy" 2>/dev/null || true
    exit 1
  fi

  if [ "$elapsed" -ge "$MAX_WAIT" ]; then
    echo "Timed out waiting for agent_app to become healthy (${MAX_WAIT}s)."
    echo "Check: docker compose ps"
    notify-send "OllamaAgent" "Failed to start: timeout" 2>/dev/null || true
    exit 1
  fi

  sleep 3
  elapsed=$((elapsed + 3))
  echo "  ...waiting (${elapsed}s) [status: ${status}]"
done

echo "agent_app is healthy. Launching window..."
source "$VENV_DIR/bin/activate"
python "$PROJECT_DIR/webapp.py"
