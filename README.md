# Electricity Price Calculator on Kubernetes

Course project for **Cloud Native Applications on Kubernetes (LTAT.06.025)**, University of Tartu.
Course materials: <https://k8s.cs.ut.ee/>

> **This is a living document.** A new lab is published every week. Each week the code, the
> manifests and this README are updated together. Sections marked *(planned)* are not done yet.

---

## 1. Purpose

The goal of the course is to learn how to build, ship and operate a cloud-native application by
running **our own Kubernetes cluster from scratch** (vanilla Kubernetes with `kubeadm`, not a
managed service). The cluster is the platform; a small microservice application is the workload
we use to practise on.

By the end of the course we want to be able to:

- containerize an application and publish its image
- install and administrate a multi-node Kubernetes cluster
- deploy stateless and stateful workloads, configuration and secrets
- expose services safely (Services, Gateway API, NetworkPolicies)
- manage storage, resources/QoS, CI/CD, monitoring, upgrades and security *(planned, later weeks)*

## 2. The problem we solve (use case)

Electricity on the Estonian market has a different price every hour, and next-day prices are
published in advance. The question the application answers:

> "I want to run a device for N hours (for example 4 h). When in the next 24 hours is it
> cheapest to do so?" Example answer: `02:00 - 06:00`.

### Application components

| Component | Role | Status |
|---|---|---|
| **Price fetcher** | Scheduled job that fetches next-day Estonian (`ee`) prices from the Elering API (`dashboard.elering.ee/api/nps/price/csv`) | Implemented |
| **History server** | HTTP API that stores price data in Garage (S3 storage) and serves it as JSON (`GET/POST /api/prices?day=YYYY-MM-DD`) | Implemented |
| **Garage** | Lightweight S3-compatible object storage, bucket `price-data` | Deployed |
| **Application server** | Computes the cheapest time window for a requested duration | *(planned)* |
| **Front-end** | Web UI for users | *(planned)* |

### Data flow

```
Elering API --> price-fetcher (CronJob) --POST JSON--> history-server --S3 API--> Garage (bucket: price-data)
                                                              ^
                                       application server / front-end (planned) read from here
```

## 3. Infrastructure and tooling

| Item | What we use |
|---|---|
| **Virtual machines** | ETAIS cloud (<https://minu.etais.ee>), the university-provided Estonian research/education cloud |
| **OS** | CentOS (image `centos10`), flavor `g5.r8c4`, 100 GB system volume |
| **Access** | SSH key-based login as user `centos`; VM is reachable only from the University network / VPN |
| **Checking / scoring** | Automated scoring server (<https://scoring.k8s.cs.ut.ee>, Nagios-based). The VM registers itself with it through a `consul` agent, and a `scoring` user with SSH key + sudo lets it probe the environment |
| **Identity file** | `/etc/identity` links the VM name to the student number |
| **Container runtime** | `containerd`, with `nerdctl` as Docker-like CLI |
| **Image building** | `buildah` |
| **Cluster** | Kubernetes installed with `kubeadm` (version pinned by the course), 1 control-plane node (also schedulable) + 2 workers |
| **CNI / networking** | Cilium (with Hubble UI for traffic visibility), Gateway API |
| **Storage** | Garage (S3-compatible) |
| **Registry** | Docker Hub (images must be reachable from all nodes), pulled through the university mirror `registry.hpc.ut.ee/mirror/` |
| **Client tools** | `kubectl`, `jq`, optionally `k9s` / Lens |

### Namespaces

| Namespace | Purpose |
|---|---|
| `production` | The real application components (price-fetcher, history-server, Garage). **This is what the scoring system checks.** |
| `test` | Experiments (nginx, PostgreSQL headless-service test) |
| `default` | echoserver test pod, Gateway test |

## 4. Essential files (on the CentOS VM, `~/`)

### Cluster setup
| File | Purpose |
|---|---|
| `kubeadm-config.yaml` | `kubeadm init` configuration (control-plane endpoint, pod/service subnets, containerd socket, systemd cgroup driver) |

### Containerization
| File / folder | Purpose |
|---|---|
| `dockerfile_lab/` (`Dockerfile`, `server.py`, `my.server.tar`) | Small Flask demo used to learn building images and exporting them as a tar |
| `fetch_prices.py` | The price-fetcher script (Elering API, posts to the history server) |
| `cronjobs` | Cron schedule file used when the fetcher ran as a cron-in-container |

### Kubernetes manifests
| File | Purpose |
|---|---|
| `pod.yaml` | echoserver Pod + ClusterIP Service (first cluster smoke test) |
| `echoserver-nodeport.yaml` | echoserver exposed as NodePort |
| `echoserver-gateway-route.yaml` | Gateway + HTTPRoute exposing echoserver via Cilium Gateway API |
| `pod-nginx.yaml`, `deployment-nginx.yaml` | nginx as bare Pod vs. managed Deployment (to see the lifecycle difference) |
| `deployment-price-fetcher.yaml` | price-fetcher as a Deployment (cron inside the container) |
| `configmap-cron-schedule.yaml` | Cron schedule as a ConfigMap mounted into the container |
| `cronjob-price-fetcher.yaml` | price-fetcher as a proper Kubernetes **CronJob** (final form) |
| `garage.toml` | Garage configuration (stored in a Secret) |
| `statefulset-garage.yaml` | Garage StatefulSet |
| `postgres-statefulset.yaml`, `postgres-service.yaml` | PostgreSQL StatefulSet + headless Service (networking experiment) |
| `network-policy.yaml` | Example NetworkPolicy for echoserver |
| `garage-network-policy.yaml` | Only the history-server may talk to Garage |

### History server (`history-server/`)
| File | Purpose |
|---|---|
| `app.py` | HTTP API (reads/writes price data in Garage via Boto3) |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Image build for the history server |
| `history-server.yaml` | Deployment + Service for the history server |
| `garage-svc.yaml` | ClusterIP Service for Garage |
| `price-data-secret.yaml` | Secret with Garage access key / secret key |

## 5. What we have achieved so far

- Personal VM created in ETAIS, reachable over SSH, registered with the scoring server
  (consul, firewall/security groups, `scoring` user, root password, `/etc/identity`).
- Price fetching implemented and automated (first with cron on the VM, then in a container).
- Application containerized with `buildah`, run with `containerd`/`nerdctl`, local registry tested.
- Working multi-node Kubernetes cluster (control plane + 2 workers) with Cilium networking
  and Hubble UI.
- Workloads in use: Pod, Deployment, ConfigMap, Secret, CronJob, StatefulSet.
- Garage object storage running in `production`, with the `price-data` bucket and an API key.
- History server implemented, containerized and deployed behind a ClusterIP Service;
  price-fetcher CronJob posts data to it.
- Networking: ClusterIP, NodePort and headless Services, Gateway API (Cilium) and
  NetworkPolicies (including isolating Garage).

## 6. Roadmap (course topics)

| Week | Topic | Status |
|---|---|---|
| 1 | Environment setup, price fetcher script | Done |
| 2 | Containerization | Done |
| 3 | Kubernetes architecture and cluster setup | Done |
| 4 | Workloads, configuration, secrets | Done |
| 5 | Services, Gateway API, networking | Done |
| 6 | Storage and database management | *(planned)* |
| 7 | Container lifecycle, QoS | *(planned)* |
| 8 | CI/CD | *(planned)* |
| 9-14 | Monitoring/logging, upgrades and operators, architecture patterns, cluster administration, security, summary | *(planned)* |
