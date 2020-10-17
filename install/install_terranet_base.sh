#!/bin/bash

pushd /usr/local/src
touch /etc/rc.local

apt-get install dialog apt-utils -y

## Install (ip)mininet VM
curl -sSL https://raw.githubusercontent.com/cnp3/ipmininet/master/ipmininet/install/build_vm.sh \
  | IPMN_REPO='https://github.com/butjar/ipmininet.git' IPMN_BRANCH='OpenR-seperate-logs-and-config-store' bash
rm -rf /etc/rc.local
dpkg-reconfigure -fnoninteractive openssh-server

## Install Komondor
git clone https://github.com/Bustel/Komondor.git
mkdir -p Komondor/Code/build
pushd Komondor/Code/build
cmake ..
make
make install
popd

## Install and start grafana
apt-get install -y apt-transport-https software-properties-common wget
wget -q -O - https://packages.grafana.com/gpg.key | apt-key add -
add-apt-repository 'deb https://packages.grafana.com/oss/deb stable main'

apt-get update && apt-get install grafana

systemctl daemon-reload
systemctl enable grafana-server --now

## Install and start influxdb
wget -qO- https://repos.influxdata.com/influxdb.key | apt-key add -
source /etc/lsb-release
echo "deb https://repos.influxdata.com/${DISTRIB_ID,,} ${DISTRIB_CODENAME} stable" | tee /etc/apt/sources.list.d/influxdb.list

apt-get update && apt-get install influxdb

systemctl unmask influxdb.service
systemctl enable influxdb --now
popd

## Install collectd
apt-get update && apt-get install -y collectd
mkdir -p /usr/share/collectd/

curl -sLo /usr/share/collectd/types.db https://raw.githubusercontent.com/collectd/collectd/master/src/types.db

systemctl unmask collectd.service
systemctl enable collectd --now
