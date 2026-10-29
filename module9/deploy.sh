#!/usr/bin/env bash
# Deploys the employee app (Node.js) and MongoDB on Kubernetes using only
# kubectl CLI commands, as the case study requires (no YAML files).
set -euo pipefail

# The case study names the "mongo" image. Its latest version (9.x) rejects this
# app: the app uses the 2015 MongoDB Node.js driver (mongodb ~2.0), which sends
# legacy OP_QUERY commands that MongoDB 6.0+ removed ("Unsupported OP_QUERY
# command: insert"). mongo:5.0 is the newest version that still accepts them.
MONGO_IMAGE="${MONGO_IMAGE:-mongo:5.0}"

# 1. MongoDB Deployment, named "mongo" (the hint in the case study)
kubectl create deployment mongo --image="$MONGO_IMAGE" --port=27017

# 2. MongoDB Service, also named "mongo". Type ClusterIP (the default):
#    reachable only inside the cluster, which is all the app needs.
#    The app reads MONGO_SERVICE_HOST / MONGO_SERVICE_PORT, which Kubernetes
#    sets for a Service named "mongo"; the name "mongo" also resolves via DNS.
kubectl expose deployment mongo --port=27017 --target-port=27017

# 3. Node.js app Deployment
kubectl create deployment employee --image=devopsedu/employee --port=8888

# 4. Node.js app Service, type NodePort so users outside the cluster can reach it:
#    <node-ip>:30888 -> Service port 8888 -> container port 8888
kubectl create service nodeport employee --tcp=8888:8888 --node-port=30888

# 5. Wait until both Deployments are ready
kubectl rollout status deployment/mongo --timeout=180s
kubectl rollout status deployment/employee --timeout=180s

kubectl get deployments,services,pods -o wide
