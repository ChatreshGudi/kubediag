from kubernetes import client
from .models import Incident, Evidence
from .collector import KubeCollector
from typing import List

class DiagnosticRule:
    def evaluate_pod(self, pod: client.V1Pod, collector: KubeCollector) -> List[Incident]:
        return []
    
    def evaluate_node(self, node: client.V1Node, collector: KubeCollector) -> List[Incident]:
        return []

def _get_resources(pod: client.V1Pod, container_name: str):
    if pod.spec and pod.spec.containers:
        for c in pod.spec.containers:
            if c.name == container_name and c.resources:
                return c.resources.requests, c.resources.limits
    return None, None

class CrashLoopRule(DiagnosticRule):
    def evaluate_pod(self, pod: client.V1Pod, collector: KubeCollector) -> List[Incident]:
        incidents = []
        if not pod.status or not pod.status.container_statuses:
            return incidents
        for cs in pod.status.container_statuses:
            is_crash = False
            state = "Unknown"
            if cs.state and cs.state.waiting and cs.state.waiting.reason == "CrashLoopBackOff":
                is_crash = True
                state = "CrashLoopBackOff"
            elif cs.state and cs.state.terminated and cs.state.terminated.reason == "Error":
                is_crash = True
                state = "Error"
            
            if is_crash:
                events = collector.get_events(pod.metadata.namespace, pod.metadata.name, "Pod")
                event_data = [{"reason": e.reason, "message": e.message} for e in events]
                logs = collector.get_pod_logs(pod.metadata.namespace, pod.metadata.name, cs.name)
                reqs, lims = _get_resources(pod, cs.name)
                
                last_state = cs.last_state.terminated if cs.last_state and cs.last_state.terminated else None
                curr_term = cs.state.terminated if cs.state and cs.state.terminated else None
                
                exit_code = curr_term.exit_code if curr_term else (last_state.exit_code if last_state else None)
                term_reason = curr_term.reason if curr_term else (last_state.reason if last_state else None)

                evidence = Evidence(
                    namespace=pod.metadata.namespace,
                    name=pod.metadata.name,
                    kind="Pod",
                    container_name=cs.name,
                    phase=pod.status.phase,
                    state=state,
                    restart_count=cs.restart_count,
                    exit_code=exit_code,
                    termination_reason=term_reason,
                    events=event_data,
                    logs=logs,
                    requests=reqs,
                    limits=lims
                )
                incidents.append(Incident("CrashLoopBackOff", "High", f"Container {cs.name} is crashing ({state})", evidence))
        return incidents

class OOMKilledRule(DiagnosticRule):
    def evaluate_pod(self, pod: client.V1Pod, collector: KubeCollector) -> List[Incident]:
        incidents = []
        if not pod.status or not pod.status.container_statuses:
            return incidents
        for cs in pod.status.container_statuses:
            is_oom = False
            exit_code = None
            if cs.state and cs.state.terminated and cs.state.terminated.reason == "OOMKilled":
                is_oom = True
                exit_code = cs.state.terminated.exit_code
            elif cs.last_state and cs.last_state.terminated and cs.last_state.terminated.reason == "OOMKilled":
                is_oom = True
                exit_code = cs.last_state.terminated.exit_code
            
            if is_oom:
                events = collector.get_events(pod.metadata.namespace, pod.metadata.name, "Pod")
                event_data = [{"reason": e.reason, "message": e.message} for e in events]
                logs = collector.get_pod_logs(pod.metadata.namespace, pod.metadata.name, cs.name)
                reqs, lims = _get_resources(pod, cs.name)

                evidence = Evidence(
                    namespace=pod.metadata.namespace,
                    name=pod.metadata.name,
                    kind="Pod",
                    container_name=cs.name,
                    phase=pod.status.phase,
                    state="OOMKilled",
                    restart_count=cs.restart_count,
                    exit_code=exit_code,
                    termination_reason="OOMKilled",
                    events=event_data,
                    logs=logs,
                    requests=reqs,
                    limits=lims
                )
                incidents.append(Incident("OOMKilled", "High", f"Container {cs.name} was OOMKilled", evidence))
        return incidents

class PendingPodRule(DiagnosticRule):
    def evaluate_pod(self, pod: client.V1Pod, collector: KubeCollector) -> List[Incident]:
        incidents = []
        if pod.status and pod.status.phase == "Pending":
            is_stuck = False
            reason = "Pod is stuck in Pending phase"
            
            # Check if it's unschedulable
            if pod.status.conditions:
                for cond in pod.status.conditions:
                    if cond.type == "PodScheduled" and cond.status == "False" and cond.reason == "Unschedulable":
                        is_stuck = True
                        reason = "Pod is Unschedulable"
                        break
            
            # Check if it's stuck pulling image
            if pod.status.container_statuses:
                for cs in pod.status.container_statuses:
                    if cs.state and cs.state.waiting and cs.state.waiting.reason in ("ImagePullBackOff", "ErrImagePull"):
                        is_stuck = True
                        reason = f"Container {cs.name} is failing to pull image"
                        break
                        
            if is_stuck:
                events = collector.get_events(pod.metadata.namespace, pod.metadata.name, "Pod")
                event_data = [{"reason": e.reason, "message": e.message} for e in events]
                
                evidence = Evidence(
                    namespace=pod.metadata.namespace,
                    name=pod.metadata.name,
                    kind="Pod",
                    phase="Pending",
                    events=event_data
                )
                incidents.append(Incident("Pending", "Medium", reason, evidence))
                
        return incidents

class ProbeFailedRule(DiagnosticRule):
    def evaluate_pod(self, pod: client.V1Pod, collector: KubeCollector) -> List[Incident]:
        incidents = []
        if not pod.status:
            return incidents
        
        events = collector.get_events(pod.metadata.namespace, pod.metadata.name, "Pod")
        probe_events = [e for e in events if e.reason in ("Unhealthy", "ProbeError")]
        
        if probe_events:
            event_data = [{"reason": e.reason, "message": e.message} for e in probe_events]
            evidence = Evidence(
                namespace=pod.metadata.namespace,
                name=pod.metadata.name,
                kind="Pod",
                phase=pod.status.phase,
                events=event_data
            )
            incidents.append(Incident("ProbeFailed", "Medium", "Readiness or Liveness probe failed", evidence))
            
        return incidents

class NotReadyNodeRule(DiagnosticRule):
    def evaluate_node(self, node: client.V1Node, collector: KubeCollector) -> List[Incident]:
        incidents = []
        if not node.status or not node.status.conditions:
            return incidents
            
        ready_condition = next((c for c in node.status.conditions if c.type == "Ready"), None)
        if ready_condition and ready_condition.status != "True":
            events = collector.get_events("default", node.metadata.name, "Node")
            event_data = [{"reason": e.reason, "message": e.message} for e in events]
            
            conds = [{"type": c.type, "status": c.status, "reason": c.reason, "message": c.message} for c in node.status.conditions]
            
            evidence = Evidence(
                namespace="",
                name=node.metadata.name,
                kind="Node",
                events=event_data,
                node_conditions=conds
            )
            incidents.append(Incident("NotReady", "High", f"Node {node.metadata.name} is not Ready", evidence))
        return incidents
