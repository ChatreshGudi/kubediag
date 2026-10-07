import argparse
import sys
from .client import get_client
from .collector import KubeCollector
from .analyzer import Analyzer
from .reporter import report_incidents

def main():
    parser = argparse.ArgumentParser(description="KubeDiag: Kubernetes Incident and Health Analyzer")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    scan_parser = subparsers.add_parser("scan", help="Scan the cluster for incidents")
    scan_parser.add_argument("--namespace", "-n", help="Namespace to scan (default: all namespaces)", default=None)
    
    diag_parser = subparsers.add_parser("diagnose", help="Diagnose a specific pod")
    diag_parser.add_argument("pod", help="Pod name")
    diag_parser.add_argument("--namespace", "-n", help="Namespace of the pod", default="default")
    
    args = parser.parse_args()
    
    try:
        api = get_client()
    except Exception as e:
        print(f"Failed to initialize Kubernetes client: {e}")
        sys.exit(1)
        
    collector = KubeCollector(api)
    analyzer = Analyzer(collector)
    
    try:
        if args.command == "scan":
            incidents = analyzer.scan_all(args.namespace)
            report_incidents(incidents)
        elif args.command == "diagnose":
            incidents = analyzer.diagnose_pod(args.namespace, args.pod)
            report_incidents(incidents)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
