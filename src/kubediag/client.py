from kubernetes import client, config
import os

def get_client() -> client.CoreV1Api:
    if "KUBERNETES_PORT" in os.environ:
        config.load_incluster_config()
    else:
        try:
            config.load_kube_config()
        except config.config_exception.ConfigException:
            pass # fallback if tests mock this
    return client.CoreV1Api()
