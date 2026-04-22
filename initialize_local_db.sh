#!/bin/bash

# initialize_local_db.sh
# Script to set up MySQL 8.0.40 Docker container and load dump files

set -e  # Exit on any error

# Configuration
MYSQL_VERSION="8.0.40"
MYSQL_PORT="13306"
MYSQL_ROOT_PASSWORD="miagent"
<<<<<<< HEAD
DUMP_DIR="./tmp/dumps"
DUMP_FILE="dump-local-midb-20260421.sql"
VOLUME_DIR="./mysql_data"
=======
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DUMP_DIR="$SCRIPT_DIR/tmp/dumps"
DUMP_FILE="20260420_local.sql"
VOLUME_DIR="$SCRIPT_DIR/mysql_data"
>>>>>>> dev

# Colors for output
RED='[0;31m'
GREEN='[0;32m'
YELLOW='[1;33m'
NC='[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
}

# Check if port is available
check_port() {
    if lsof -Pi :$MYSQL_PORT -sTCP:LISTEN -t >/dev/null ; then
        log_warning "Port $MYSQL_PORT is already in use"
        log_info "Attempting to stop any existing MySQL container on this port..."
        docker stop mysql-local || true
        docker rm mysql-local || true
    fi
}

# Extract database name from dump file, kmj20260421화, USE midb를 우선적으로 읽도록 수정
extract_db_name() {
    if [ ! -f "$DUMP_DIR/$DUMP_FILE" ]; then
        log_error "Dump file $DUMP_DIR/$DUMP_FILE not found"
        exit 1
    fi

    # Prefer USE statement because it is simpler and less error-prone
    DB_NAME=$(grep -i '^USE ' "$DUMP_DIR/$DUMP_FILE" | head -1 | sed -E 's/^USE[[:space:]]+`?([^` ;]+)`?;?/\1/I')

    if [ -z "$DB_NAME" ]; then
        DB_NAME=$(grep -i '^CREATE DATABASE' "$DUMP_DIR/$DUMP_FILE" | head -1 | sed -E 's/^CREATE DATABASE[[:space:]]+(IF NOT EXISTS[[:space:]]+)?`?([^` ;]+)`?.*/\2/I')
    fi

    if [ -z "$DB_NAME" ]; then
        log_warning "Could not automatically detect database name from dump file"
        DB_NAME="midb"
        log_info "Using default database name: $DB_NAME"
    else
        log_info "Detected database name from dump file: $DB_NAME"
    fi
}

# Pull MySQL image
pull_mysql_image() {
    log_info "Pulling MySQL $MYSQL_VERSION image..."
    docker pull mysql:$MYSQL_VERSION
}

# Start MySQL container with proper authentication
start_mysql_container() {
    log_info "Starting MySQL container on port $MYSQL_PORT..."
    
    # Create volume directory if it doesn't exist
    mkdir -p "$VOLUME_DIR"

    docker run -d \
        --name mysql-local \
        -p $MYSQL_PORT:3306 \
        -e MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD \
        -e MYSQL_DATABASE=$DB_NAME \
        -e MYSQL_ROOT_HOST='%' \
        -v "$VOLUME_DIR:/var/lib/mysql" \
        -v "$DUMP_DIR:/docker-entrypoint-initdb.d" \
        mysql:$MYSQL_VERSION

    log_info "MySQL container started successfully"
}

# Grant privileges to root user for remote access
grant_root_privileges() {
    log_info "Granting root privileges for remote access..."
    docker exec mysql-local mysql -u root -p$MYSQL_ROOT_PASSWORD -e "ALTER USER 'root'@'%' IDENTIFIED BY '$MYSQL_ROOT_PASSWORD';"
    docker exec mysql-local mysql -u root -p$MYSQL_ROOT_PASSWORD -e "GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;"
    docker exec mysql-local mysql -u root -p$MYSQL_ROOT_PASSWORD -e "FLUSH PRIVILEGES;"
    log_info "Root privileges granted for remote access"
}

# Wait for MySQL to be ready
wait_for_mysql() {
    log_info "Waiting for MySQL to be ready..."
    local timeout=300  # Increased timeout to 5 minutes
    local count=0
    local retry_count=0
    local max_retries=3

    # First check if container is running
    if ! docker ps --filter "name=mysql-local" | grep -q mysql-local; then
        log_error "MySQL container is not running"
        exit 1
    fi

    # Give container some time to start before first health check
    sleep 10

    while [ $count -lt $timeout ]; do
        if docker exec mysql-local mysqladmin ping -h 127.0.0.1 -P 3306 --silent; then
            log_info "MySQL is ready!"
            return 0
        fi

        sleep 1
        ((count++))

        # Show progress every 30 seconds
        if [ $((count % 30)) -eq 0 ]; then
            log_info "Still waiting for MySQL to be ready... ($count seconds elapsed)"
        fi

        # Check container status periodically
        if ! docker ps --filter "name=mysql-local" | grep -q mysql-local; then
            log_error "MySQL container stopped unexpectedly"
            exit 1
        fi
    done

    log_error "MySQL failed to start within $timeout seconds"
    log_error "Container logs:"
    docker logs mysql-local
    exit 1
}

# Main execution
main() {
    log_info "Starting MySQL initialization process..."

    check_docker
    check_port
    extract_db_name
    pull_mysql_image
    start_mysql_container
    wait_for_mysql
    grant_root_privileges

log_info "MySQL initialization completed successfully!"
log_info "MySQL is running on port $MYSQL_PORT"
log_info "Root password: $MYSQL_ROOT_PASSWORD"
log_info "Database name: $DB_NAME"
log_info "Data is persisted in: $VOLUME_DIR"
log_info "Dump files are mounted from: $DUMP_DIR"
log_info "Connection command: mysql -h 127.0.0.1 -P $MYSQL_PORT -u root -p$MYSQL_ROOT_PASSWORD"
}

# Handle script arguments
case "${1:-}" in
    start)
        main
        ;;
    stop)
        log_info "Stopping MySQL container..."
        docker stop mysql-local || true
        docker rm mysql-local || true
        log_info "MySQL container stopped"
        ;;
    status)
        if docker ps --filter "name=mysql-local" | grep -q mysql-local; then
            log_info "MySQL container is running"
        else
            log_info "MySQL container is not running"
        fi
        ;;
    logs)
        docker logs mysql-local
        ;;
    cleanup)
        log_info "Cleaning up MySQL container and data..."
        docker stop mysql-local || true
        docker rm mysql-local || true
        rm -rf "$VOLUME_DIR"
        log_info "Cleanup completed"
        ;;
    *)
        echo "Usage: $0 {start|stop|status|logs|cleanup}"
        echo ""
        echo "Commands:"
        echo "  start    - Start MySQL container and load dump files"
        echo "  stop     - Stop MySQL container"
        echo "  status   - Check if MySQL container is running"
        echo "  logs     - Show MySQL container logs"
        echo "  cleanup  - Stop container and remove all data"
        exit 1
        ;;
esac