from .collector import KubeCollector
from .rules import CrashLoopRule, OOMKilledRule, PendingPodRule, ProbeFailedRule, NotReadyNodeRule
from typing import List, Optional
from .models import Incident

class Analyzer:
    def __init__(self, collector: KubeCollector):
        self.collector = collector
        self.rules = [
            CrashLoopRule(),
            OOMKilledRule(),
            PendingPodRule(),
            ProbeFailedRule(),
            NotReadyNodeRule()
        ]

    def scan_all(self, namespace: Optional[str] = None) -> List[Incident]:
        pods = self.collector.get_pods(namespace)
        nodes = self.collector.get_nodes() if not namespace else []
        
        incidents = []
        for pod in pods:
            for rule in self.rules:
                incidents.extend(rule.evaluate_pod(pod, self.collector))
        
        for node in nodes:
            for rule in self.rules:
                incidents.extend(rule.evaluate_node(node, self.collector))
                
        return incidents

    def diagnose_pod(self, namespace: str, pod_name: str) -> List[Incident]:
        pods = self.collector.get_pods(namespace)
        pod = next((p for p in pods if p.metadata.name == pod_name), None)
        if not pod:
            raise ValueError(f"Pod {pod_name} not found in namespace {namespace}")
            
        incidents = []
        for rule in self.rules:
            incidents.extend(rule.evaluate_pod(pod, self.collector))
        return incidents
