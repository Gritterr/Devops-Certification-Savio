# Module 9 Case Study: Multi-tier App on Kubernetes

Deploys the `devopsedu/employee` Node.js app and its MongoDB database on Kubernetes using only `kubectl` commands, then adds an employee in the app and retrieves it on the Get Employee page.

## Files

| File | Purpose |
|---|---|
| [deploy.sh](deploy.sh) | The deployment: four `kubectl create`/`expose` commands, then waits until both apps are ready |
| [evidence/](evidence/) | Command output and browser screenshots |

## What gets deployed

```
 browser ──► <node-ip>:30888 ──► Service "employee" (NodePort) ──► employee pod :8888
                                                                       │
                                     mongodb://mongo:27017/employee    ▼
                                  Service "mongo" (ClusterIP) ──► mongo pod :27017
```

| Object | Created by | Why |
|---|---|---|
| Deployment `mongo` | `kubectl create deployment mongo --image=mongo:5.0 --port=27017` | Runs MongoDB and restarts it if it fails |
| Service `mongo` | `kubectl expose deployment mongo --port=27017` | ClusterIP: a fixed internal address for the database, reachable only inside the cluster |
| Deployment `employee` | `kubectl create deployment employee --image=devopsedu/employee --port=8888` | Runs the Node.js app |
| Service `employee` | `kubectl create service nodeport employee --tcp=8888:8888 --node-port=30888` | NodePort: opens port 30888 on the node so users outside the cluster can reach the app |

## Concepts

- **Pod**: the smallest unit Kubernetes runs; here, one container each for the app and the database.
- **Deployment**: keeps the requested number of pods running and replaces failed ones. `kubectl set image` on a Deployment does a rolling update.
- **Service**: a stable name and IP in front of pods, which get new IPs whenever they restart. It finds its pods by label (`app=mongo`, `app=employee`); `kubectl create deployment` sets that label automatically.
- **ClusterIP vs NodePort**: ClusterIP (the default) is internal only, which is right for a database. NodePort also opens a port (30000–32767) on every node, which is how external users reach the app.
- **Why the database must be named `mongo`**: the app connects to `mongodb://$MONGO_SERVICE_HOST:$MONGO_SERVICE_PORT/employee`. For a Service named `mongo`, Kubernetes sets exactly those variables in pods started after it ([evidence/4-clean-deploy.txt](evidence/4-clean-deploy.txt) shows `MONGO_SERVICE_HOST=10.43.192.40`). The image also defaults `MONGO_SERVICE_HOST` to `mongo`, which cluster DNS resolves to the same Service. Any other name breaks both.
- **Order matters**: `deploy.sh` creates the `mongo` Service before the app, so the variables exist when the app's pod starts.

## Why MongoDB 5.0 and not the latest `mongo`

The case study names the `mongo` image. Its latest version (MongoDB 9.0.4 at the time of the run) rejects this app:

```
MongoError: Unsupported OP_QUERY command: insert. The client driver may require an upgrade.
```

The app was built in 2018 with Node 4 and the 2015 MongoDB driver (`mongodb ~2.0`), which sends commands using the legacy `OP_QUERY` protocol. MongoDB 6.0 removed it. `mongo:5.0` is the newest version that still accepts it, so `deploy.sh` uses `mongo:5.0` by default. The switch was made with a CLI rolling update: `kubectl set image deployment/mongo mongo=mongo:5.0`. See [evidence/1b-mongo-latest-error.txt](evidence/1b-mongo-latest-error.txt) and [evidence/2-pin-mongo-5.0.txt](evidence/2-pin-mongo-5.0.txt).

## Cluster

A single-node **k3s** cluster (Kubernetes v1.30.6) on a CentOS 7 VM (`10.79.140.67`), installed with:

```bash
curl -sfL https://get.k3s.io | sudo INSTALL_K3S_VERSION="v1.30.6+k3s1" INSTALL_K3S_SKIP_SELINUX_RPM=true sh -s - --disable traefik --disable servicelb
mkdir -p ~/.kube && sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config && sudo chown "$USER" ~/.kube/config && chmod 600 ~/.kube/config
export KUBECONFIG=$HOME/.kube/config
```

- `--disable traefik --disable servicelb` keeps k3s off ports 80 and 443, which another app on the VM uses.
- `export KUBECONFIG=...` is needed because k3s's `kubectl` otherwise reads `/etc/rancher/k3s/k3s.yaml`, which only root can read.
- kind (Kubernetes in Docker) was tried first but needs cgroup namespaces, which this VM's Linux 4.4 kernel lacks.

## Run it

```bash
./deploy.sh
# open http://<node-ip>:30888 → AddEmployee → fill in the form → Add
#                             → GetEmployee → enter the ID → Get
```

To remove: `kubectl delete service mongo employee && kubectl delete deployment mongo employee`

## Evidence

| File | What it shows |
|---|---|
| [1-deploy-mongo-latest.txt](evidence/1-deploy-mongo-latest.txt) | First deploy with the unpinned `mongo` image: all objects created and running |
| [1b-mongo-latest-error.txt](evidence/1b-mongo-latest-error.txt) | Adding an employee fails against MongoDB 9.0.4 (`Unsupported OP_QUERY command`) |
| [2-pin-mongo-5.0.txt](evidence/2-pin-mongo-5.0.txt) | `kubectl set image` to `mongo:5.0` and the rolling update |
| [3-add-and-get-employee.txt](evidence/3-add-and-get-employee.txt) | Add and get employee E101 with `curl` after the switch |
| [4-clean-deploy.txt](evidence/4-clean-deploy.txt) | Everything removed and redeployed from scratch with the final `deploy.sh`; `MONGO_SERVICE_HOST` injected into the app |
| [5-home-page.png](evidence/5-home-page.png) | App home page at `http://10.79.140.67:30888` |
| [6-add-employee-form.png](evidence/6-add-employee-form.png), [7-add-employee-result.png](evidence/7-add-employee-result.png) | Employee E202 entered and added |
| [8-get-employee-result.png](evidence/8-get-employee-result.png) | **Get Employee returns E202 with the same details** |

## Limitation

MongoDB has no persistent volume, so employee data is lost if the `mongo` pod is recreated (as happened between evidence 3 and 4). The case study does not ask for persistence. Adding a PersistentVolumeClaim mounted at `/data/db` would keep the data.
