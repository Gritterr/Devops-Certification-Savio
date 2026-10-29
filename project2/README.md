# Certification Project 2: CI/CD to Kubernetes for Abstergo Corp.

When a developer pushes to `master`, a Jenkins pipeline builds and tests a Docker image of the app and pushes it to Docker Hub. It then deploys the image to a Kubernetes cluster with a rolling update. A HorizontalPodAutoscaler adds pods under load, and Prometheus and Grafana monitor the app.

- **Application repository** (Node.js app, `Jenkinsfile`, `Dockerfile`, Kubernetes manifest): https://github.com/Gritterr/cicd-pipeline-train-schedule-autodeploy. The brief's link (`bhavukm/...`) no longer exists, so this is a fork of the original it was copied from, `linuxacademy/cicd-pipeline-train-schedule-autodeploy`.
- **Docker Hub**: https://hub.docker.com/r/saviochristopher/train-schedule
- **This folder**: the monitoring stack, the Jenkins job config, and the evidence

## Architecture

```
 developer ── git push ──► GitHub: Gritterr/cicd-pipeline-train-schedule-autodeploy (master)
                                  │ polled every minute
                                  ▼
 Jenkins master (Mac) ── Pipeline job "Project2-Train-Schedule" (stages from the repo's Jenkinsfile)
                                  │ runs on the agent "test-server" over SSH
                                  ▼
 ┌─ Test server, CentOS 7 VM 10.79.140.67: Docker + single-node k3s cluster ─────────────┐
 │  1 Build & Test Image ─► 2 Push to Docker Hub ─► 3 Deploy to Kubernetes ─► 4 Smoke Test │
 │                          saviochristopher/train-schedule:<build>                          │
 │                                 │ the cluster pulls the image from Docker Hub             │
 │                                 ▼                                                         │
 │  Deployment (2–5 pods) ◄── HorizontalPodAutoscaler (CPU > 50% of request)                 │
 │  Service NodePort 30080 ──► http://10.79.140.67:30080/                                    │
 │                                                                                           │
 │  monitoring: Prometheus :30090 ◄── kubelet/cAdvisor, kube-state-metrics                   │
 │              Grafana :30030 (Train Schedule dashboard)                                    │
 └───────────────────────────────────────────────────────────────────────────────────────────┘
```

## Files

**Application repository**

| File | Purpose |
|---|---|
| `Jenkinsfile` | The pipeline: build & test image, push to Docker Hub, deploy, smoke test. Polls GitHub every minute |
| `Dockerfile` | Two stages: install dependencies and run the unit tests, then a small runtime image (Node 20 Alpine, production dependencies only, non-root user) |
| `k8s/train-schedule.yml` | Deployment (probes, CPU/memory requests and limits, rolling update), NodePort Service on 30080, HorizontalPodAutoscaler (2–5 pods at 50% CPU) |

**This folder**

| File | Purpose |
|---|---|
| [jenkins/Project2-Train-Schedule.xml](jenkins/Project2-Train-Schedule.xml) | The Jenkins Pipeline job: "Pipeline script from SCM" pointing at the fork's `Jenkinsfile`, polling every minute |
| [monitoring/prometheus.yml](monitoring/prometheus.yml) | Prometheus with read-only access to node metrics. Scrapes pod CPU and memory (cAdvisor) and kube-state-metrics |
| [monitoring/kube-state-metrics.yml](monitoring/kube-state-metrics.yml) | Exposes deployment, pod and HPA state (such as the replicas the HPA wants) as metrics |
| [monitoring/grafana.yml](monitoring/grafana.yml) | Grafana with the Prometheus data source and the dashboard provisioned from files |
| [monitoring/train-schedule-dashboard.json](monitoring/train-schedule-dashboard.json) | Dashboard: pods available, HPA replicas, CPU as % of request, CPU and memory per pod |
| [monitoring/deploy-monitoring.sh](monitoring/deploy-monitoring.sh) | Applies the above; generates Grafana's admin password into a Kubernetes Secret |
| [evidence/](evidence/) | Screenshots, console logs, HPA load test, cluster state |

## The pipeline, step by step

| Stage | What happens |
|---|---|
| Trigger | Jenkins polls GitHub every minute (`pollSCM`). A new commit on `master` starts a build |
| Checkout | Jenkins reads the `Jenkinsfile` from the repo, then checks the repo out on the agent `test-server` |
| Build & Test Image | `docker build -t saviochristopher/train-schedule:<build> -t …:latest .` The Dockerfile runs `npm ci` and the mocha tests, so a failing test fails the build and nothing is pushed |
| Push to Docker Hub | Logs in with the Jenkins credential `docker-hub` (an access token, masked in the log) and pushes both tags. The login lives in a temporary directory that is deleted afterwards |
| Deploy to Kubernetes | Fills this build's image tag into `k8s/train-schedule.yml`, runs `kubectl apply` and waits for `kubectl rollout status`. If the new pods never become ready, it runs `kubectl rollout undo` |
| Smoke Test | The home page must show this build's number, and `/trains` must return data; otherwise the deployment is rolled back |
| Cleanup | Removes the build's image from the agent; the cluster pulls from Docker Hub |

## Concepts

- **Pipeline as code**: the stages live in a `Jenkinsfile` in the application repo, versioned and reviewed with the code. Jenkins only knows where the repo is.
- **Continuous integration and deployment**: every commit is built, tested, published and deployed with no manual step. The image tag is the build number, so every deployment can be traced to a build and a commit.
- **Image registry**: Docker Hub stores every version. The cluster pulls the exact tag the pipeline deployed, so any node can run it and older builds can be redeployed.
- **Multi-stage Dockerfile**: the first stage installs everything and runs the tests; the final image copies only what the app needs (165 MB instead of about 900 MB for the original `node:carbon`).
- **Deployment and rolling update**: Kubernetes keeps the requested number of pods running and replaces them one at a time on a new version (`maxSurge: 1`, `maxUnavailable: 0`), so the site stays up during a deploy.
- **Probes**: the readiness probe sends traffic to a pod only once its page loads; the liveness probe restarts a pod that stops responding. (The app's `/break` endpoint makes it return errors, which shows the liveness probe at work.)
- **Service**: one stable address (NodePort 30080) that load-balances across however many pods exist.
- **HorizontalPodAutoscaler**: every 15 seconds it compares pod CPU (from metrics-server) with the target, 50% of the 100m request, and changes the replica count between 2 and 5. It scales down only after 5 minutes of low load, to avoid flapping.
- **Monitoring**: Prometheus pulls ("scrapes") metrics every 15 seconds and stores them as time series; Grafana queries Prometheus to draw dashboards. cAdvisor (built into the kubelet) reports container CPU and memory; kube-state-metrics reports what Kubernetes intends (replicas, HPA targets).
- **Poll SCM vs webhook**: GitHub cannot reach this Jenkins to deliver a webhook, so Jenkins asks GitHub instead, at the cost of up to a minute's delay.

## Setup (one time)

**Cluster**: k3s v1.30 on the test server (single node, includes metrics-server). The Jenkins agent user's `~/.kube/config` gives `kubectl` access.

**Docker Hub**: an access token with Read & Write scope, stored in Jenkins as the credential `docker-hub` (kind *Username with password*).

**Jenkins** (2.580.1 on the master): the Pipeline and Pipeline Stage View plugins; the agent `test-server` from Project 1 (Docker and `kubectl` are installed there). Create the job from [jenkins/Project2-Train-Schedule.xml](jenkins/Project2-Train-Schedule.xml):

```bash
curl -u admin:<token> -H 'Content-Type: text/xml' --data-binary @jenkins/Project2-Train-Schedule.xml \
  "<jenkins>/createItem?name=Project2-Train-Schedule"
```

**Monitoring**, on a machine with `kubectl` access:

```bash
monitoring/deploy-monitoring.sh
# Grafana: http://10.79.140.67:30030, user admin, password:
kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.password}' | base64 -d
```

## Evidence

Jenkins and Grafana show IST; the VM's own clock (in the `.txt` files) is UTC.

| What it shows | Files |
|---|---|
| Pipeline Stage View: both builds green across all stages | [1-jenkins-stage-view.png](evidence/1-jenkins-stage-view.png) |
| **A push triggered the pipeline**: commit `190df86` pushed at 21:11:03, build #2 "Started by an SCM change" at 21:12:11, deployed and smoke-tested at 21:13:16 | [2-build2-push-triggered.png](evidence/2-build2-push-triggered.png), [console-build2.txt](evidence/console-build2.txt) |
| Images pushed to Docker Hub, tagged by build number | [3-docker-hub-tags.png](evidence/3-docker-hub-tags.png) |
| The live app, showing the build that is deployed | [4-app-live.png](evidence/4-app-live.png) |
| Prometheus scraping all three targets | [5-prometheus-targets.png](evidence/5-prometheus-targets.png) |
| **Autoscaling**: under load, CPU rose to about 400% of the request and the HPA scaled 2 → 5 pods within a minute, then back to 2 five minutes after the load stopped | [6-grafana-dashboard.png](evidence/6-grafana-dashboard.png), [hpa-load-test.txt](evidence/hpa-load-test.txt), [kubectl-state.txt](evidence/kubectl-state.txt) |
| First deployment (build #1), from the first poll after the job was created | [console-build1.txt](evidence/console-build1.txt) |

**Load test**: six parallel loops requesting the app's `/generate-cpu-load` endpoint for 270 seconds, run on the test server against `http://localhost:30080`.
