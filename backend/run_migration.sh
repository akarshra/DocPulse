#!/bin/bash
# Migration execution script for PostgreSQL migration
# This script handles the complete migration process

set -e

echo "=========================================="
echo "DocPulse PostgreSQL Migration"
echo "=========================================="
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed"
    exit 1
fi

echo "Step 1: Cleaning up existing containers and volumes..."
docker-compose down -v || true
echo "✓ Cleanup complete"
echo ""

echo "Step 2: Building and starting services..."
docker-compose up -d --build
echo "✓ Services started"
echo ""

echo "Step 3: Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker-compose exec -T db pg_isready -U docpulse > /dev/null 2>&1; then
        echo "✓ PostgreSQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "✗ PostgreSQL failed to start"
        docker-compose logs db
        exit 1
    fi
    echo "  Attempt $i/30..."
    sleep 1
done
echo ""

echo "Step 4: Running Alembic migrations..."
docker-compose exec -T backend alembic upgrade head
echo "✓ Migrations applied"
echo ""

echo "Step 5: Verifying migration..."
docker-compose exec -T backend python verify_migration.py
echo ""

echo "=========================================="
echo "✓ Migration Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Access the API at http://localhost:8000"
echo "2. Access the frontend at http://localhost:3000"
echo "3. Test file upload functionality"
echo ""
