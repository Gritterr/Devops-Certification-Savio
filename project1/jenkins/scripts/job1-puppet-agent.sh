#!/bin/bash
# Job 1: install and configure the Puppet agent on the test server.
# Runs on the Jenkins agent "test-server". Works on CentOS/RHEL and Ubuntu.
set -eu
PUPPET_SERVER="${PUPPET_SERVER:-puppet}"   # Puppet's conventional server name
PUPPET=/opt/puppetlabs/bin/puppet

if [ -f /etc/redhat-release ]; then
  rhel="$(rpm -E %rhel)"
  rpm -q puppet7-release >/dev/null 2>&1 || sudo rpm -Uvh "https://yum.puppet.com/puppet7-release-el-${rhel}.noarch.rpm"
  # Only Puppet's repo is needed; skipping the others avoids slow or dead OS mirrors
  rpm -q puppet-agent >/dev/null 2>&1 || sudo yum -y -q --disablerepo='*' --enablerepo=puppet7 install puppet-agent
else
  codename="$(. /etc/os-release && echo "$VERSION_CODENAME")"
  if ! dpkg -s puppet-agent >/dev/null 2>&1; then
    curl -fsSLo /tmp/puppet7-release.deb "https://apt.puppet.com/puppet7-release-${codename}.deb"
    sudo dpkg -i /tmp/puppet7-release.deb && sudo apt-get update -q
    sudo apt-get install -y -q puppet-agent
  fi
fi

# Configure: which Puppet server to use and how this node identifies itself
sudo "$PUPPET" config set server "$PUPPET_SERVER" --section main
sudo "$PUPPET" config set certname "$(hostname -f)" --section main
sudo "$PUPPET" config set runinterval 30m --section agent

echo "Puppet agent version: $("$PUPPET" --version)"
echo "Configured server:    $(sudo "$PUPPET" config print server --section main)"
echo "Configured certname:  $(sudo "$PUPPET" config print certname --section main)"

# Prove the agent works by applying a one-line manifest locally
sudo "$PUPPET" apply -e "notify { 'Puppet agent on $(hostname) is installed and configured': }"

# The agent service is left stopped: this setup has no Puppet server for it to
# contact. With a server, start it with:
#   sudo puppet resource service puppet ensure=running enable=true
