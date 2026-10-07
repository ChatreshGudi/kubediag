import pytest
from kubernetes import client
from kubediag.rules import CrashLoopRule, OOMKilledRule, PendingPodRule, ProbeFailedRule, NotReadyNodeRule
from kubediag.collector import KubeCollector
from kubediag.models import Incident

class MockCollector(KubeCollector):
    def __init__(self):
        self.events = []
        self.logs = "Mock log output"
        
    def get_events(self, namespace, obj_name, obj_kind):
        return self.events
        
    def get_pod_logs(self, namespace, pod_name, container_name, tail_lines=20):
        return self.logs

@pytest.fixture
def collector():
    return MockCollector()

def create_pod(phase="Running", container_states=None, conditions=None):
    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(name="test-pod", namespace="default"),
        status=client.V1PodStatus(phase=phase),
        spec=client.V1PodSpec(containers=[client.V1Container(name="test-container")])
    )
    if container_states:
        pod.status.container_statuses = [
            client.V1ContainerStatus(
                name="test-container", 
                image="test-image", 
                image_id="test-image-id", 
                ready=False, 
                restart_count=1,
                state=state,
                last_state=last_state
            ) for state, last_state in container_states
        ]
    if conditions:
        pod.status.conditions = [
            client.V1PodCondition(type=c["type"], status=c["status"], reason=c.get("reason"), message=c.get("message"))
            for c in conditions
        ]
    return pod

def test_crash_loop_rule(collector):
    state = client.V1ContainerState(waiting=client.V1ContainerStateWaiting(reason="CrashLoopBackOff"))
    last_state = client.V1ContainerState(terminated=client.V1ContainerStateTerminated(exit_code=1, reason="Error"))
    pod = create_pod(container_states=[(state, last_state)])
    
    rule = CrashLoopRule()
    incidents = rule.evaluate_pod(pod, collector)
    
    assert len(incidents) == 1
    assert incidents[0].type == "CrashLoopBackOff"
    assert incidents[0].evidence.restart_count == 1
    assert incidents[0].evidence.exit_code == 1

def test_oom_killed_rule(collector):
    state = client.V1ContainerState(terminated=client.V1ContainerStateTerminated(reason="OOMKilled", exit_code=137))
    pod = create_pod(container_states=[(state, None)])
    
    rule = OOMKilledRule()
    incidents = rule.evaluate_pod(pod, collector)
    
    assert len(incidents) == 1
    assert incidents[0].type == "OOMKilled"
    assert incidents[0].evidence.exit_code == 137

def test_pending_pod_rule(collector):
    pod = create_pod(phase="Pending", conditions=[{"type": "PodScheduled", "status": "False", "reason": "Unschedulable"}])
    
    rule = PendingPodRule()
    incidents = rule.evaluate_pod(pod, collector)
    
    assert len(incidents) == 1
    assert incidents[0].type == "Pending"

def test_probe_failed_rule(collector):
    pod = create_pod(conditions=[{"type": "Ready", "status": "False"}])
    
    # Mock events
    mock_event = client.CoreV1Event(
        metadata=client.V1ObjectMeta(name="ev1"),
        involved_object=client.V1ObjectReference(),
        reason="Unhealthy",
        message="Liveness probe failed"
    )
    collector.events = [mock_event]
    
    rule = ProbeFailedRule()
    incidents = rule.evaluate_pod(pod, collector)
    
    assert len(incidents) == 1
    assert incidents[0].type == "ProbeFailed"

def test_not_ready_node_rule(collector):
    node = client.V1Node(
        metadata=client.V1ObjectMeta(name="test-node"),
        status=client.V1NodeStatus(
            conditions=[
                client.V1NodeCondition(type="Ready", status="False", reason="KubeletNotReady", message="kubelet stopped")
            ]
        )
    )
    
    rule = NotReadyNodeRule()
    incidents = rule.evaluate_node(node, collector)
    
    assert len(incidents) == 1
    assert incidents[0].type == "NotReady"
    assert incidents[0].evidence.node_conditions[0]["reason"] == "KubeletNotReady"
