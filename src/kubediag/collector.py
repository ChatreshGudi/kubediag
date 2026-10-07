from kubernetes import client
from typing import List, Optional

class KubeCollector:
    def __init__(self, api: client.CoreV1Api):
        self.api = api
        self._event_cache = {}

    def get_pods(self, namespace: Optional[str] = None) -> List[client.V1Pod]:
        # Let exceptions bubble up. It's critical to fail on RBAC/Auth errors rather than hide them.
        if namespace:
            return self.api.list_namespaced_pod(namespace).items
        return self.api.list_pod_for_all_namespaces().items

    def get_nodes(self) -> List[client.V1Node]:
        return self.api.list_node().items

    def get_events(self, namespace: str, obj_name: str, obj_kind: str) -> List[client.CoreV1Event]:
        # Cache events per namespace to avoid N+1 API queries (1 query per pod)
        if namespace not in self._event_cache:
            self._event_cache[namespace] = self.api.list_namespaced_event(namespace).items
            
        return [
            e for e in self._event_cache[namespace] 
            if e.involved_object.name == obj_name and e.involved_object.kind == obj_kind
        ]
    
    def get_pod_logs(self, namespace: str, pod_name: str, container_name: str, tail_lines: int = 20) -> Optional[str]:
        # We can still swallow log fetching errors, since missing logs shouldn't break the whole scan,
        # but we should catch the specific kubernetes ApiException
        try:
            from kubernetes.client.exceptions import ApiException
            return self.api.read_namespaced_pod_log(pod_name, namespace, container=container_name, tail_lines=tail_lines)
        except Exception:
            return None
