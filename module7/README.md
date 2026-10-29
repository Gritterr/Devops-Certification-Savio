# Module 7 Case Study: Company Website on Docker Swarm

Packages the company website in a Docker image based on Apache `httpd`, pushes it to Docker Hub, and runs it as a replicated service on a Docker Swarm with port 80 exposed. The website files live in a volume outside the containers.

## Files

| File | Objective | Purpose |
|---|---|---|
| [fetch-website.sh](fetch-website.sh) | 1. Download the website | Fetches the case-study repo at a pinned commit and copies `Case-study app/` into `website/` |
| [Dockerfile](Dockerfile) | 2. Web server, 3. Volumes | Builds on `httpd:2.4`, copies the site into `htdocs`, declares `htdocs` as a volume |
| [.dockerignore](.dockerignore) | 2 | Keeps Sass sources, `.DS_Store` files and project files out of the image |
| [docker-stack.yml](docker-stack.yml) | 4. Image from Docker Hub, 6. Swarm deploy | Service with 3 replicas, port 80, and one shared named volume |

`website/` is downloaded, not committed (about 31 MB). Run `./fetch-website.sh` before building.

**About the files:** the PDF describes a Drupal agency, but the supplied website is a static HTML, CSS and JavaScript site. Static files need only a web server, so `httpd` serves them as they are.

## Concepts

- **Image**: a read-only package of a filesystem plus a default command. Ours is `httpd` plus the website files.
- **Dockerfile**: the recipe for an image. Each instruction (`FROM`, `COPY`, `VOLUME`) adds a layer on top of the base image.
- **Container**: a running instance of an image. Its own filesystem is thrown away when the container is removed.
- **Volume**: storage managed by Docker that lives outside any container. Data in a volume survives containers being stopped, replaced or scaled. This is how the website data is kept "outside the container".
- **Registry (Docker Hub)**: a place to store images. Pushing lets any machine `docker pull` the image. A swarm needs it so every node can get the same image.
- **Swarm**: Docker's built-in cluster mode. One or more managers schedule work; workers run it. `docker swarm init` turns a machine into the first manager.
- **Service and replicas**: a service is the desired state, for example "3 copies of this image on port 80". Swarm keeps that many containers (replicas) running and replaces any that fail.
- **Routing mesh**: when a service publishes a port, every swarm node accepts traffic on it and forwards it to a healthy replica, even on a node without one.
- **Stack**: a group of services and volumes described in one file (`docker-stack.yml`) and deployed with `docker stack deploy`.

## How the volume keeps one source of files

1. The image contains the website in `/usr/local/apache2/htdocs`, and the Dockerfile marks that folder as a `VOLUME`.
2. The stack mounts the named volume `website-data` on that folder for every replica.
3. The first time an empty named volume is mounted, Docker copies the image's files into it. After that, all replicas read and write the same volume.
4. Changing a file in the volume changes it for every replica, with no rebuild.

On a single-node swarm, every replica is on the same machine and shares the volume directly. On a multi-node swarm, a plain local volume would exist separately on each node. Backing `website-data` with an NFS share (commented in `docker-stack.yml`) gives every node the same source.

## Steps

```bash
# 1. Download the website files
./fetch-website.sh

# 2-3. Build the image (the Dockerfile adds httpd and declares the volume)
docker build -t <dockerhub-user>/company-website:1.0 .

# 4. Push to Docker Hub (log in first; Docker asks for your password or token)
docker login
docker push <dockerhub-user>/company-website:1.0

# 5. Create the swarm (this machine becomes the manager)
docker swarm init --advertise-addr <host-ip>

# 6. Deploy and check (leave IMAGE unset to use the local company-website:1.0 build)
IMAGE=<dockerhub-user>/company-website:1.0 docker stack deploy -c docker-stack.yml company
docker stack services company        # expect 3/3 replicas
curl -s http://<host-ip>/ | head     # the site's index.html
```

## Results

Run on a CentOS 7 VM (`10.79.140.67`) with Docker 26.1.4, as a single-node swarm.

| Objective | Status | Evidence |
|---|---|---|
| 1. Download the website | Done (pinned commit `77063e2`) | `fetch-website.sh` |
| 2. Dockerfile on `httpd` | Done: `company-website:1.0`, 147 MB | [evidence/1-build.txt](evidence/1-build.txt) |
| 3. Website data in a volume | Done: named volume `company_website-data` | [evidence/3-verify-site-and-volume.txt](evidence/3-verify-site-and-volume.txt) |
| 4. Push to Docker Hub | Done: `saviochristopher/company-website:1.0` | [evidence/5-dockerhub-push.txt](evidence/5-dockerhub-push.txt), [evidence/7-dockerhub-repo.png](evidence/7-dockerhub-repo.png) |
| 5. Swarm cluster | Done: VM is the swarm leader | [evidence/2-swarm-deploy.txt](evidence/2-swarm-deploy.txt) |
| 6. Deploy on port 80, shared volume | Done: 3/3 replicas on `*:80` | [evidence/2-swarm-deploy.txt](evidence/2-swarm-deploy.txt), [evidence/3-verify-site-and-volume.txt](evidence/3-verify-site-and-volume.txt), [evidence/4-website-port-80.png](evidence/4-website-port-80.png) |

How the shared volume was checked: all three replicas mount `company_website-data` from the same host folder. A test file written once into that folder was readable in all three containers and was served on every request through port 80. The test file was then removed.

The site also loads from another machine (`http://10.79.140.67/`, HTTP 200), shown in [evidence/4-website-port-80.png](evidence/4-website-port-80.png).

The swarm join token is left out of the evidence on purpose: anyone with it can join machines to the cluster.

## Push to Docker Hub

Public image: https://hub.docker.com/r/saviochristopher/company-website (tag `1.0`, digest `sha256:4aa5ebdc8272…`).

```bash
docker login -u saviochristopher               # a Docker Hub access token was used as the password
docker tag company-website:1.0 saviochristopher/company-website:1.0
docker push saviochristopher/company-website:1.0
cd ~/module7 && IMAGE=saviochristopher/company-website:1.0 docker stack deploy -c docker-stack.yml company
```

- `docker tag` gives the existing image a second name in the form `<user>/<repo>:<tag>`; it copies nothing.
- During the push, 6 of 7 layers were "Mounted from library/httpd": Docker Hub already had the `httpd` base layers, so only the website layer was uploaded.
- The last command switched the running service to the Docker Hub image, which is what a multi-node swarm needs so other nodes can pull it. Swarm replaced the replicas one at a time (a rolling update), so the site stayed up. See [evidence/6-redeploy-from-dockerhub.txt](evidence/6-redeploy-from-dockerhub.txt).
- The website files did not change on redeploy: they live in the `company_website-data` volume, and Docker only copies image files into a volume when it is empty.

## Installing Docker on CentOS 7

CentOS 7 is end of life, and the mirrors its base and extras repos point to no longer serve packages. Docker's own repo still has `docker-ce 26.1.4` for CentOS 7, but its dependencies (`container-selinux`, `fuse-overlayfs` and others) come from CentOS's repos. They were installed from `vault.centos.org` through a temporary repo file, which was removed afterward.
