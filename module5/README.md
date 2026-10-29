# Module 5 Case Study: Configuration Management with Ansible

Provisions Apache Tomcat and Apache Maven on the production hosts with two Ansible roles called from one playbook. Target: a CentOS 7 VM (`10.79.140.67`).

## Files

| File | Purpose |
|---|---|
| [ansible.cfg](ansible.cfg) | Points Ansible at the inventory and the roles folder |
| [inventory/hosts.ini](inventory/hosts.ini) | The hosts to manage, in the `prod` group |
| [site.yml](site.yml) | The playbook: runs the `tomcat` and `maven` roles on `prod` with sudo |
| [requirements.yml](requirements.yml) | Ansible collections the roles need (`ansible.posix`, `community.general`) |
| [roles/tomcat/](roles/tomcat/) | Java 8, `tomcat` user, Tomcat 8.5.31 in `/opt/tomcat`, systemd service |
| [roles/maven/](roles/maven/) | Maven 3.3.9 in `/opt`, `mvn` via `alternatives`, JDK set in `/etc/mavenrc` |
| [evidence/](evidence/) | Output of each playbook run and the final checks |

Each role has `defaults/main.yml` (variables), `tasks/main.yml` (steps; each one names the PDF command it replaces), and for Tomcat a `templates/` unit file and `handlers/`.

## Concepts

- **Inventory**: the list of machines Ansible manages. Ansible connects over SSH, so a target needs only SSH and Python. `hosts: prod` in the playbook means "run on that group".
- **Playbook**: YAML that maps hosts to work. Ours is short because the work lives in roles.
- **Role**: a standard folder layout that packages related work (tasks, variables, templates, handlers) so it can be reused. The case study asks for one role per tool.
- **Task and module**: each task calls one module (`yum`, `user`, `get_url`, `unarchive`, `template`, `systemd`). A module describes the end state, such as "this package is present", rather than the command to run.
- **Idempotency**: running the playbook again changes nothing once the host is correct. This is what fixes "inconsistent servers": every run brings each host to the same state. See the `changed=0` run below.
- **Handlers**: tasks that run only when something notifies them. Here, Tomcat restarts only when its unit file or config permissions change.
- **Templates (Jinja2)**: `tomcat.service.j2` has `{{ variables }}` filled in at run time, so the Java path and install folder are not hardcoded.
- **`become: true`**: runs tasks with sudo, replacing the `sudo` in each PDF command.

## Run it

```bash
cd module5
ansible-galaxy collection install -r requirements.yml
ansible-playbook site.yml --syntax-check
ansible-playbook site.yml --check --diff   # preview without changing anything
ansible-playbook site.yml                  # apply
```

**Ansible version:** CentOS 7 ships Python 3.6, which current Ansible (2.17+) cannot manage. These runs used **ansible-core 2.12.10**, which still supports it. On a newer OS, current Ansible works as is.

## Changes from the PDF commands

| PDF | This project | Why |
|---|---|---|
| `apt-get` / `default-jdk` | `yum` / `java-1.8.0-openjdk-devel` | The target is CentOS, not Ubuntu |
| Tomcat and Maven mirror URLs | `archive.apache.org` URLs (variables) | The PDF mirrors are dead |
| Maven downloaded to `/home/edureka/Downloads` | `/tmp` | That user does not exist on the target |
| `JAVA_HOME=/usr/lib/jvm/java-1.8.0-openjdk-amd64/jre` | `/usr/lib/jvm/jre-1.8.0-openjdk` (variable) | That is the Ubuntu path; CentOS uses a different one |
| `After=network.targetd` | `After=network.target` | Typo in the PDF |
| `python-software-properties`, `ppa:webupd8team/java` | Dropped | Ubuntu-only and dead |
| `mkdir /opt/tomcat` twice | Once | Duplicate step |
| (not in PDF) | `/etc/mavenrc` sets Maven's `JAVA_HOME` | See "Problems found" below |
| (not in PDF) | Optional firewalld rule for 8080, off by default | firewalld is not installed on this VM |

## Problems found while running, and fixes

1. **Tomcat crash-looped.** The first version of the role ran `chmod g+rx` on the `conf` folder only. The PDF's `chmod -R g+r conf` is recursive for a reason: Tomcat's config files ship readable only by their owner, so the `tomcat` user could not read `server.xml` and Tomcat exited at startup (`Permissions incorrect, read permission is not allowed`). Fixed by making the task recursive, as in the PDF, and having it restart Tomcat when it changes.
2. **`mvn -v` failed.** This VM's `/etc/environment` sets `JAVA_HOME` to a JDK path that does not exist. Maven was installed correctly but could not start. Rather than edit a system-wide file other software may depend on, the role writes `/etc/mavenrc`, which Maven's launcher reads at startup, so Maven always uses the Java 8 JDK the role installs.

## Evidence

| File | What it shows |
|---|---|
| [run1-maven-install.txt](evidence/run1-maven-install.txt) | Maven installed (`changed=3`). Tomcat tasks show `ok` because an earlier interrupted run had already installed Tomcat; that output was not kept |
| [run2-fix-conf-permissions.txt](evidence/run2-fix-conf-permissions.txt) | Permission fix applied and Tomcat restarted by the handler (`changed=2`) |
| [run3-maven-java-home.txt](evidence/run3-maven-java-home.txt) | `/etc/mavenrc` added (`changed=1`) |
| [run4-idempotency.txt](evidence/run4-idempotency.txt) | **Second clean run: `changed=0 failed=0`** |
| [verification.txt](evidence/verification.txt) | `mvn -v` reports Maven 3.3.9 on Java 1.8.0_272; Tomcat `active`, `enabled`, `HTTP 200` with title "Apache Tomcat/8.5.31" |

Port 8080 was checked from the VM itself (`curl localhost:8080`). Access from other machines depends on the VM's network rules.

## Note

Tomcat 8.5.31 and Maven 3.3.9 are old releases with known vulnerabilities. They are used because the case study names them. A real production server should use current versions; only the version variables in `defaults/main.yml` need to change.
