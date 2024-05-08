# FAQ

## Technical help

### Get the Load Balancer Public IP address

```bash
kubectl get service -n ingress-nginx -o jsonpath='{.items[?(@.spec.type=="LoadBalancer")].status.loadBalancer.ingress[0].ip}'
```

### Get the `dockerconfigjson` from the secret

```bash
kubectl get secret ocir-secret --output="jsonpath={.data.\.dockerconfigjson}" | base64 --decode | jq
```
