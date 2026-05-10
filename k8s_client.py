import logging
from kubernetes import client, config

logger = logging.getLogger("k8s-mcp-server")

try:
    config.load_incluster_config()
    logger.info("Loaded in-cluster Kubernetes config")
except Exception:
    config.load_kube_config()
    logger.info("Loaded kubeconfig")

v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()
