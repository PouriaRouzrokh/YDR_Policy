import argparse
import asyncio
import os
import sys
import logging
from pathlib import Path

def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(Path("data/logs/application.log"))
        ]
    )
    return logging.getLogger(__name__)

def main():
    """Main entry point for the application."""
    logger = setup_logging()

    parser = argparse.ArgumentParser(description="Yale Radiology Policies RAG Application")
    subparsers = parser.add_subparsers(dest="mode", help="Mode to run the application in")

    # Mode 1: MCP Server mode
    mcp_parser = subparsers.add_parser("mcp", help="Run the MCP server for policy retrieval tools")
    mcp_parser.add_argument("--port", type=int, default=8001, help="Port to run the MCP server on")
    mcp_parser.add_argument("--host", default="0.0.0.0", help="Host to bind the MCP server to")
    mcp_parser.add_argument("--transport", choices=["http", "stdio"], default="http",
                           help="Transport mechanism (http or stdio)")
    mcp_parser.add_argument("--db-uri", help="Database URI (overrides config)")

    # Mode 2: Backend API mode
    api_parser = subparsers.add_parser("api", help="Run the Backend API server with Chat Agent")
    api_parser.add_argument("--host", default="0.0.0.0", help="Host to bind the API server to")
    api_parser.add_argument("--port", type=int, default=8000, help="Port to run the API server on")
    api_parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    api_parser.add_argument("--mcp-url", help="URL of the MCP server (default: http://localhost:8001)")
    api_parser.add_argument("--db-uri", help="Database URI (overrides config)")

    # Mode 3: Frontend mode (for development)
    frontend_parser = subparsers.add_parser("frontend", help="Run the frontend development server")
    frontend_parser.add_argument("--port", type=int, default=3000, help="Port to run the frontend on")
    frontend_parser.add_argument("--api-url", help="URL of the Backend API (default: http://localhost:8000)")

    # Mode 4: Data Collection/Policy Processing mode
    data_parser = subparsers.add_parser("policy", help="Process policies for the database")
    data_parser.add_argument("--task", choices=["crawl", "scrape", "process", "add"],
                            required=True, help="Policy processing task to run")
    data_parser.add_argument("--url", help="URL of the policy or policy index page")
    data_parser.add_argument("--urls-file", help="File containing list of URLs to process")
    data_parser.add_argument("--follow-links", action="store_true",
                        help="Follow links from the provided URL(s)")
    data_parser.add_argument("--depth", type=int, default=1,
                        help="Link following depth when --follow-links is enabled")
    data_parser.add_argument("--admin-id", type=int, help="ID of admin performing the operation")
    data_parser.add_argument("--db-uri", help="Database URI (overrides config)")

    # Full application mode (runs all components)
    full_parser = subparsers.add_parser("full", help="Run the complete application stack")
    full_parser.add_argument("--api-port", type=int, default=8000, help="Port for the Backend API")
    full_parser.add_argument("--mcp-port", type=int, default=8001, help="Port for the MCP server")
    full_parser.add_argument("--frontend-port", type=int, default=3000, help="Port for the frontend")
    full_parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    full_parser.add_argument("--db-uri", help="Database URI (overrides config)")

    # Initialize database schema
    init_parser = subparsers.add_parser("init-db", help="Initialize the database schema")
    init_parser.add_argument("--db-uri", help="Database URI (overrides config)")

    args = parser.parse_args()

    if not args.mode:
        parser.print_help()
        sys.exit(1)

    try:
        if args.mode == "policy":
            if args.task == "crawl" or args.task == "all":
                from ydrpolicy.data_collection.crawl.crawl import main as crawl_main
                crawl_main()

            elif args.task == "scrape" or args.task == "all":
                from ydrpolicy.data_collection.scrape.scrape import main as scrape_main
                scrape_main()

            elif args.task == "process" or args.task == "add":
                from ydrpolicy.backend.services.policy_processor import process_policies_cli
                asyncio.run(process_policies_cli(
                    url=args.url,
                    urls_file=args.urls_file,
                    admin_id=args.admin_id,
                    follow_links=args.follow_links,
                    depth=args.depth,
                    db_url=args.db_uri
                ))

        elif args.mode == "mcp":
            logger.info(f"Starting MCP Server on {args.host}:{args.port} with {args.transport} transport")
            from ydrpolicy.mcp_server.server import run_server
            run_server(host=args.host, port=args.port, transport=args.transport, db_uri=args.db_uri)

        elif args.mode == "api":
            logger.info(f"Starting Backend API Server on {args.host}:{args.port}, Debug={args.debug}")
            from ydrpolicy.backend.app import start_backend
            start_backend(host=args.host, port=args.port, debug=args.debug,
                         mcp_url=args.mcp_url, db_uri=args.db_uri)

        elif args.mode == "frontend":
            logger.info(f"Starting Frontend Server on port {args.port}")
            # Change directory to frontend and run npm command
            frontend_dir = Path(__file__).parent / "ydrpolicy" / "frontend"
            if not frontend_dir.exists():
                logger.error(f"Frontend directory not found: {frontend_dir}")
                sys.exit(1)

            os.chdir(frontend_dir)
            api_url = args.api_url or "http://localhost:8000"
            os.environ["NEXT_PUBLIC_API_URL"] = api_url
            os.system(f"npm run dev -- --port {args.port}")

        elif args.mode == "full":
            logger.info("Starting Full Application Stack")
            # This would start all components using multiprocessing
            import subprocess
            import threading

            # Function to run a component in a separate process
            def run_component(cmd, name):
                logger.info(f"Starting {name} with command: {' '.join(cmd)}")
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )

                # Handle stdout and stderr
                def log_output(stream, level):
                    for line in stream:
                        if level == "info":
                            logger.info(f"[{name}] {line.strip()}")
                        else:
                            logger.error(f"[{name}] {line.strip()}")

                # Start threads for logging
                threading.Thread(target=log_output, args=(process.stdout, "info"), daemon=True).start()
                threading.Thread(target=log_output, args=(process.stderr, "error"), daemon=True).start()

                return process

            # Start MCP Server
            mcp_cmd = [sys.executable, __file__, "mcp", "--port", str(args.mcp_port)]
            if args.db_uri:
                mcp_cmd.extend(["--db-uri", args.db_uri])
            mcp_process = run_component(mcp_cmd, "MCP Server")

            # Give MCP server time to start
            import time
            time.sleep(2)

            # Start Backend API
            api_cmd = [sys.executable, __file__, "api", "--port", str(args.api_port),
                      "--mcp-url", f"http://localhost:{args.mcp_port}"]
            if args.debug:
                api_cmd.append("--debug")
            if args.db_uri:
                api_cmd.extend(["--db-uri", args.db_uri])
            api_process = run_component(api_cmd, "Backend API")

            # Give API server time to start
            time.sleep(2)

            # Start Frontend
            frontend_cmd = [sys.executable, __file__, "frontend", "--port", str(args.frontend_port),
                           "--api-url", f"http://localhost:{args.api_port}"]
            frontend_process = run_component(frontend_cmd, "Frontend")

            # Wait for all processes to complete (or user interruption)
            try:
                frontend_process.wait()
            except KeyboardInterrupt:
                logger.info("Shutting down all components...")
                for process in [frontend_process, api_process, mcp_process]:
                    process.terminate()
                    process.wait()
                logger.info("All components shut down")

        elif args.mode == "init-db":
            logger.info("Initializing database schema")
            from ydrpolicy.backend.scripts.initialize_database import initialize_database
            initialize_database(db_uri=args.db_uri)

    except KeyboardInterrupt:
        logger.info("Application interrupted. Shutting down...")
    except Exception as e:
        logger.exception(f"Error running application in {args.mode} mode: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()