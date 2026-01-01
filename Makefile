.PHONY: restart stop

stop:
	@echo "=========================================="
	@echo "Stopping NumbyAI - All Services"
	@echo "=========================================="
	@echo ""
	@echo "Stopping servers on all ports..."
	@lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "✓ Backend server (port 8000) stopped" || echo "  No process on port 8000"
	@lsof -ti:3000 | xargs kill -9 2>/dev/null && echo "✓ Frontend dev server (port 3000) stopped" || echo "  No process on port 3000"
	@lsof -ti:4444 | xargs kill -9 2>/dev/null && echo "✓ Static server (port 4444) stopped" || echo "  No process on port 4444"
	@echo ""
	@echo "Checking for any remaining uvicorn processes..."
	@pkill -f "uvicorn app.main:asgi_app" 2>/dev/null && echo "✓ Additional uvicorn processes stopped" || echo "  No additional uvicorn processes found"
	@echo ""
	@echo "=========================================="
	@echo "✓ All services stopped"
	@echo "=========================================="

restart:
	@echo "=========================================="
	@echo "Restarting NumbyAI - Full System Restart"
	@echo "=========================================="
	@echo ""
	@echo "Step 1: Stopping all servers..."
	@lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	@lsof -ti:3000 | xargs kill -9 2>/dev/null || true
	@lsof -ti:4444 | xargs kill -9 2>/dev/null || true
	@sleep 1
	@echo "✓ All servers stopped"
	@echo ""
	@echo "Step 2: Running database migrations..."
	@cd mcp-server && .venv/bin/alembic upgrade head > /dev/null 2>&1 && echo "✓ Database migrations applied" || echo "⚠ Database migration check completed"
	@echo ""
	@echo "Step 3: Building frontend widgets..."
	@cd web && npm run build > /dev/null 2>&1 && echo "✓ Frontend built successfully" || (echo "✗ Frontend build failed" && exit 1)
	@echo ""
	@echo "Step 4: Starting backend server on port 8000..."
	@cd mcp-server && .venv/bin/uvicorn app.main:asgi_app --host 0.0.0.0 --port 8000 --reload > /tmp/numbyai-backend.log 2>&1 &
	@sleep 3
	@echo "✓ Backend server starting (logs: /tmp/numbyai-backend.log)"
	@echo ""
	@echo "Step 5: Verifying services are responding..."
	@sleep 2
	@curl -s http://localhost:8000/health > /dev/null && echo "✓ Backend health check passed" || echo "⚠ Backend not responding yet (may need a moment)"
	@echo ""
	@echo "=========================================="
	@echo "✓ Restart complete!"
	@echo "=========================================="
	@echo "Backend:  http://localhost:8000"
	@echo "Health:   http://localhost:8000/health"
	@echo "Widgets: http://localhost:8000/widgets (frontend widgets served here)"
	@echo "Test:     http://localhost:8000/test-widget?widget=dashboard"
	@echo ""
	@echo "Note: Frontend widgets are built and served by the backend."
	@echo "      No separate frontend server needed."
	@echo ""
	@echo "Backend logs: tail -f /tmp/numbyai-backend.log"
	@echo "To stop: lsof -ti:8000 | xargs kill -9"
