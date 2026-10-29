#!/bin/bash
# Job 2: push the Ansible configuration that installs Docker on the test server.
# Runs on the Jenkins master (built-in node), where Ansible is installed.
set -eu
cd /Users/savio.christopher/Devops-Certification-Savio/project1/ansible
# ansible-core 2.12: the last release that can manage CentOS 7's Python 3.6
~/.local/share/venvs/ansible-core-2.12/bin/ansible-playbook install-docker.yml
