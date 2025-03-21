import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser(description="Yale Radiology Policies RAG Application")
    subparsers = parser.add_subparsers(dest="mode", help="Mode to run the application in")

    # MCP Server mode
    mcp_parser = subparsers.add_parser("mcp", help="Run the MCP server")
    mcp_parser.add_argument("--port", type=int, default=8001, help="Port to run the MCP server on")
    mcp_parser.add_argument("--transport", choices=["http", "stdio"], default="http",
                           help="Transport mechanism (http or stdio)")

    # Backend API mode
    api_parser = subparsers.add_parser("api", help="Run the Backend API server")
    api_parser.add_argument("--host", default="0.0.0.0", help="Host to bind the API server to")
    api_parser.add_argument("--port", type=int, default=8000, help="Port to run the API server on")
    api_parser.add_argument("--debug", action="store_true", help="Run in debug mode")

    # Data Collection mode
    data_parser = subparsers.add_parser("data", help="Run data collection tasks")
    data_parser.add_argument("--task", choices=["crawl", "scrape", "all"],
                            required=True, help="Data collection task to run")

    # Frontend mode (for development)
    frontend_parser = subparsers.add_parser("frontend", help="Run the frontend development server")
    frontend_parser.add_argument("--port", type=int, default=3000, help="Port to run the frontend on")

    args = parser.parse_args()

    if not args.mode:
        parser.print_help()
        sys.exit(1)

    if args.mode == "data":
        if args.task == "crawl" or args.task == "all":
            from data_collection.crawl.crawl import main as crawl_main
            crawl_main()

        if args.task == "scrape" or args.task == "all":
            from data_collection.scrape.scrape import main as scrape_main
            scrape_main()

    elif args.mode == "mcp":
        # from mcp_server.server import run_server
        # run_server(port=args.port, transport=args.transport)
        raise NotImplementedError("MCP server not implemented yet")

    elif args.mode == "api":
        # from backend.app import start_backend
        # start_backend(host=args.host, port=args.port, debug=args.debug)
        raise NotImplementedError("Backend API server not implemented yet")

    elif args.mode == "frontend":
        # Change directory to frontend and run npm command
        # os.chdir("frontend")
        # os.system(f"npm run dev -- --port {args.port}")
        raise NotImplementedError("Frontend development server not implemented yet")

if __name__ == "__main__":
    main()