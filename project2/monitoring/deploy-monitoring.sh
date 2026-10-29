#!/bin/bash
# Deploy Prometheus, kube-state-metrics and Grafana into the "monitoring"
# namespace. Run on a machine where kubectl can reach the cluster; safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"

kubectl apply -f prometheus.yml   # also creates the namespace
kubectl apply -f kube-state-metrics.yml

# Grafana's admin password: generated once, kept only in the cluster
kubectl -n monitoring get secret grafana-admin >/dev/null 2>&1 ||
  kubectl -n monitoring create secret generic grafana-admin \
    --from-literal=password="$(head -c 18 /dev/urandom | base64)"

kubectl -n monitoring create configmap grafana-dashboards \
  --from-file=train-schedule-dashboard.json --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f grafana.yml

kubectl -n monitoring rollout status deployment/prometheus --timeout=180s
kubectl -n monitoring rollout status deployment/kube-state-metrics --timeout=180s
kubectl -n monitoring rollout status deployment/grafana --timeout=180s

echo "Prometheus: http://<node>:30090   Grafana: http://<node>:30030 (user admin)"
echo "Grafana password: kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.password}' | base64 -d"
