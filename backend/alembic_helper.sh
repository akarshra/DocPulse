#!/bin/bash
# Alembic helper script for common migration operations

set -e

usage() {
    cat << EOF
Alembic Migration Helper

Usage: ./alembic_helper.sh [COMMAND] [OPTIONS]

Commands:
    migrate              Apply all pending migrations
    generate [MESSAGE]   Generate a new migration from model changes
    downgrade [N]        Rollback N migrations (default: 1)
    history              Show migration history
    current              Show current migration version
    help                 Show this help message

Examples:
    ./alembic_helper.sh migrate
    ./alembic_helper.sh generate "Add user_id column"
    ./alembic_helper.sh downgrade 2
    ./alembic_helper.sh history

EOF
}

# Ensure docker-compose is running
check_docker() {
    if ! docker-compose ps backend > /dev/null 2>&1; then
        echo "Error: Backend service is not running"
        echo "Please run: docker-compose up -d"
        exit 1
    fi
}

case "$1" in
    migrate)
        check_docker
        echo "Applying migrations..."
        docker-compose exec -T backend alembic upgrade head
        echo "✓ Migrations applied"
        ;;
    generate)
        if [ -z "$2" ]; then
            echo "Error: Please provide a migration message"
            echo "Usage: ./alembic_helper.sh generate \"Your migration message\""
            exit 1
        fi
        check_docker
        echo "Generating migration: $2"
        docker-compose exec -T backend alembic revision --autogenerate -m "$2"
        echo "✓ Migration generated"
        ;;
    downgrade)
        check_docker
        STEPS=${2:-1}
        echo "Rolling back $STEPS migration(s)..."
        docker-compose exec -T backend alembic downgrade -$STEPS
        echo "✓ Rollback complete"
        ;;
    history)
        check_docker
        echo "Migration history:"
        docker-compose exec -T backend alembic history
        ;;
    current)
        check_docker
        echo "Current migration:"
        docker-compose exec -T backend alembic current
        ;;
    help|--help|-h|"")
        usage
        ;;
    *)
        echo "Unknown command: $1"
        usage
        exit 1
        ;;
esac
