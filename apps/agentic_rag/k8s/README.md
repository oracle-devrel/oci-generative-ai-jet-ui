# Agentic RAG Kubernetes Deployment

This directory contains the manifests and instructions to deploy the Agentic RAG application on Kubernetes.

> **Note**: These instructions have been verified with a local **Kind** cluster.

## Prerequisites

1.  **Docker**: Ensure Docker is installed and running.
2.  **Kubectl**: Installed and configured.
3.  **Kind** (Optional but recommended for testing): [Installation Guide](https://kind.sigs.k8s.io/docs/user/quick-start/#installation).

## 1. Build and Load Docker Image

Because the application requires embedding models (`gemma3:270m`) that are pulled at runtime, and Kubernetes environments often have strict network/DNS policies that can block these downloads, we use a **self-contained build strategy**.

We build the image locally with the model pre-pulled (or pulled during optimized startup) and load it directly into the cluster.

### Step 1: Build the Image
Navigate to the application root (`apps/agentic_rag`) and build the image. We use `--network=host` to ensure the build process can access the internet to download dependencies and models.

```bash
# Run from apps/agentic_rag/
docker build --network=host -t agentic-rag:k8s-test-v2 .
```

### Step 2: Load Image into Cluster (Kind Only)
If you are using Kind, you must load the image into the cluster nodes so they can access it without pulling from a remote registry.

```bash
kind load docker-image agentic-rag:k8s-test-v2 --name agentic-rag-cluster
```

> **Note**: If using a remote cluster (OKE, EKS, etc.), you would tag and push this image to your container registry instead.

## 2. Deploy to Kubernetes

The Web application manifests are located in `local-deployment/`.

1.  **Apply ConfigMap and PVCs**:
    ```bash
    kubectl apply -f local-deployment/configmap.yaml
    kubectl apply -f local-deployment/pvcs.yaml
    ```

2.  **Deploy the Application**:
    ```bash
    kubectl apply -f local-deployment/deployment.yaml
    ```

3.  **Expose the Service**:
    ```bash
    kubectl apply -f local-deployment/service.yaml
    ```

## 3. Verify Deployment

Check the status of the pods:

```bash
kubectl get pods -w
```

You should see the pod transition to `Running` state.

To verify the application logs and ensure the LLM service (Ollama) has started successfully:

```bash
kubectl logs -f -l app=agentic-rag
```

You should see output indicating:
- "Ollama is ready."
- "Starting Gradio application..."

## 4. Access the Application

The service is exposed via `LoadBalancer` (or `NodePort` depending on your cluster capability).

To get the external IP or port:

```bash
kubectl get svc agentic-rag
```

If using Kind or Minikube, you might need to port-forward if an external IP isn't assigned:

```bash
# Forward local port 7860 to the service
kubectl port-forward svc/agentic-rag 7860:80
```

Then access the app at `http://localhost:7860`.

## Directory Structure

*   `local-deployment/`: Contains standard Kubernetes manifests (`deployment`, `service`, `configmap`, `pvc`).