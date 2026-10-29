# Certification Project 1: CI/CD for AppleBite's PHP Application

A push to the `master` branch of the application repository starts a Jenkins pipeline that prepares a test server with Puppet and Ansible, then builds the PHP website into a Docker image and deploys it there. If the deployment fails, the running container is deleted.

- **Application repository** (PHP website + Dockerfile): https://github.com/Gritterr/projCert (fork of `edureka-devops/projCert`)
- **This folder**: the Ansible playbook, the Jenkins job scripts and configs, and the evidence

## Architecture

```
 developer ── git push ──► GitHub: Gritterr/projCert (master)
                                  │  polled every minute
                                  ▼
 ┌─ Jenkins master (Mac: Jenkins, Ansible, Git) ───────────────────────────────┐
 │  Job1-Puppet-Agent ──► Job2-Ansible-Docker ──► Job3-Build-Deploy-PHP        │
 │  runs on test-server    runs on master,         runs on test-server         │
 │                         Ansible over SSH        └─ on failure: delete       │
 │                                                     container (task 4)      │
 └──────────────────────────────┬──────────────────────────────────────────────┘
                                │ SSH (Jenkins agent "test-server")
                                ▼
 Test server (CentOS 7 VM 10.79.140.67): Puppet agent, Docker,
 container "php-website" on port 8081 ──► http://10.79.140.67:8081/
```

## Files

| File | Purpose |
|---|---|
| [ansible/install-docker.yml](ansible/install-docker.yml) | Job 2's playbook: installs and starts Docker on the test server (CentOS/RHEL or Ubuntu/Debian) |
| [ansible/inventory.ini](ansible/inventory.ini) | The test server's address and SSH login |
| [jenkins/scripts/job1-puppet-agent.sh](jenkins/scripts/job1-puppet-agent.sh) | Job 1: install and configure the Puppet agent |
| [jenkins/scripts/job2-ansible-docker.sh](jenkins/scripts/job2-ansible-docker.sh) | Job 2: run the playbook |
| [jenkins/scripts/job3-build-deploy.sh](jenkins/scripts/job3-build-deploy.sh) | Job 3: build the image, replace the container, smoke-test the site |
| [jenkins/scripts/job3-on-failure.sh](jenkins/scripts/job3-on-failure.sh) | Task 4: delete the container when Job 3 fails |
| [jenkins/jobs/](jenkins/jobs/) | Jenkins `config.xml` for the 3 jobs and the Build Pipeline view |
| [jenkins/build-job-configs.py](jenkins/build-job-configs.py) | Generates `jenkins/jobs/*.xml` from the scripts, so the two never drift apart |
| [evidence/](evidence/) | Console logs, build history and screenshots |

The **Dockerfile** lives in the application repository:

```dockerfile
FROM devopsedu/webapp                    # Ubuntu 18.04 + Apache 2.4 + PHP 7.0
RUN rm -f /var/www/html/index.html       # the base image's placeholder page would hide index.php
COPY website/ /var/www/html/
EXPOSE 80
CMD ["apachectl", "-D", "FOREGROUND"]    # the base image's default command is /bin/bash
```

## The pipeline, step by step

| Task in the brief | Job | What happens |
|---|---|---|
| Trigger on push to master | Job 1's **Poll SCM** (`* * * * *`) | Jenkins checks GitHub every minute; a new commit on `master` starts Job 1 |
| 1. Install and configure the Puppet agent on the slave node | `Job1-Puppet-Agent` (on `test-server`) | Adds Puppet's repo, installs `puppet-agent` 7, sets `server`, `certname` and `runinterval`, then applies a one-line manifest to prove the agent works |
| 2. Push an Ansible configuration to install Docker | `Job2-Ansible-Docker` (on the master) | Runs `install-docker.yml` against the test server over SSH |
| 3. Pull the website and Dockerfile, build and deploy | `Job3-Build-Deploy-PHP` (on `test-server`) | Checks out `master`, builds `projcert-php:<build>`, replaces the `php-website` container on port 8081, and fails unless the home page loads |
| 4. If Job 3 fails, delete the running container | Post-build Task on Job 3 | When the log shows `Build step 'Execute shell' marked build as failure`, runs `docker rm -f php-website` |

Each job starts the next only if it succeeds. The **Build Pipeline view** `Project1-Pipeline` shows each run across the three jobs.

## Concepts

- **Continuous integration and deployment**: every change pushed to `master` is built, tested (the smoke test in Job 3) and deployed with no manual steps, so feedback reaches developers within minutes.
- **Master and agent (slave)**: the Jenkins master schedules work and holds configuration; an agent runs builds on another machine. Here the agent `test-server` is the test server itself, so Jobs 1 and 3 run directly on it. Jenkins connects over SSH and runs a small Java process there.
- **Poll SCM vs webhook**: with a webhook, GitHub calls Jenkins the moment a push happens, but that needs Jenkins reachable from the internet. Polling has Jenkins ask GitHub instead (`git ls-remote` every minute), so it works behind a firewall, at the cost of up to a minute's delay.
- **Puppet vs Ansible**: both are configuration management tools. Puppet is pull-based: an agent on each server fetches its configuration from a Puppet server. Ansible is push-based and agentless: the master connects over SSH and applies the playbook. The brief uses both: Job 1 installs Puppet's agent, Job 2 pushes Docker with Ansible.
- **Idempotency**: re-running Jobs 1 and 2 changes nothing once the server is in the right state. Job 2 reports `changed=0` when Docker is already installed.
- **Image and container**: Job 3 builds a new image tagged with the build number, then replaces the running container with one from it. Old images stay, so a previous build can be redeployed.
- **Failure handling**: the smoke test (`curl` + `grep` for the site's title) makes a bad deployment fail the job; the Post-build Task then removes the broken container instead of leaving it running.

## Setup (one time)

**Test server (the "slave node")**: Python 3.6 and openssh-server were already installed. Git 1.8.3 was installed manually (`yum install git`). Jenkins agents need Java 17+, and CentOS 7 only ships up to Java 11, so a Temurin 21 runtime was unpacked into `/home/admin/jenkins-agent/jre21` (checksum verified).

**SSH key for Jenkins**: a dedicated key pair (`~/.ssh/jenkins_test_server`) authorized for `admin` on the test server. Jenkins stores it as the credential `test-server-ssh` for the agent connection, and Ansible uses the same key.

**Jenkins master (Mac)**: Jenkins 2.580.1 with the **Build Pipeline**, **Post-build Task**, **Git** and **SSH Build Agents** plugins. Ansible: `ansible-core 2.12.10` in `~/.local/share/venvs/ansible-core-2.12`, because CentOS 7's Python 3.6 is too old for current Ansible.

**Jenkins configuration**: agent `test-server` (label `test-server`, remote root `/home/admin/jenkins-agent`, SSH with credential `test-server-ssh`), then the three jobs and the view from `jenkins/jobs/`:

```bash
curl -u admin:<token> -H 'Content-Type: text/xml' --data-binary @jenkins/jobs/Job3-Build-Deploy-PHP.xml "<jenkins>/createItem?name=Job3-Build-Deploy-PHP"
# repeat for Job2 and Job1, then: --data-binary @jenkins/jobs/Project1-Pipeline.view.xml "<jenkins>/createView?name=Project1-Pipeline"
```

## Evidence

| What it shows | Files |
|---|---|
| Pipeline view: three runs, all green | [1-pipeline-view.png](evidence/1-pipeline-view.png) |
| Test server connected as a Jenkins agent | [2-test-server-agent.png](evidence/2-test-server-agent.png) |
| **A push to master triggered the pipeline**: commit `5d0970d` pushed at 19:30:01, Job 1 #3 "Started by an SCM change" at 19:30:10, change live at 19:34:11 | [3-job1-console-push-triggered.png](evidence/3-job1-console-push-triggered.png), [console-job1-3-push-triggered.txt](evidence/console-job1-3-push-triggered.txt), [build-history.txt](evidence/build-history.txt) |
| Puppet agent 7.34.0 installed, configured, and applying a manifest | same Job 1 console |
| Ansible playbook run against the test server | [4-job2-console-ansible.png](evidence/4-job2-console-ansible.png), [console-job2-3.txt](evidence/console-job2-3.txt) |
| Image built and container deployed | [5-job3-console-deploy.png](evidence/5-job3-console-deploy.png), [console-job3-3.txt](evidence/console-job3-3.txt) |
| **Job 3 failure deletes the container** (run with `SIMULATE_FAILURE=true`) | [6-job3-console-failure-cleanup.png](evidence/6-job3-console-failure-cleanup.png), [console-job3-4-simulated-failure.txt](evidence/console-job3-4-simulated-failure.txt) |
| Site redeployed after the failure test | [console-job3-5-restore.txt](evidence/console-job3-5-restore.txt) |
| The live website, showing the pushed change | [7-php-website-live.png](evidence/7-php-website-live.png) |

**Testing the failure path**: Job 3 has a `SIMULATE_FAILURE` parameter (default `false`). Set to `true`, it deploys and then fails on purpose, so task 4 can be shown on demand without breaking the application code. Runs started by the pipeline always use `false`.

**Why pipeline runs #1 and #2 built the same commit**: when the jobs were first created, Job 1 had no build history, so each poll during that first run counted as a change and queued one more run. Once a build had recorded commit `bbe824b`, polling reported "No changes" until the next push.
