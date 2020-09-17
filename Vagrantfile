# vi: syntax=ruby
# vi: filetype=ruby

$dev_provisioning = <<-'SCRIPT'
sudo influx -execute "CREATE DATABASE customerstats"
sudo influx -execute "CREATE DATABASE switchstats"
sudo pip3 install -e /vagrant
sudo systemctl restart collectd.service
sudo systemctl restart influxdb.service
sudo systemctl restart influxd.service
sudo systemctl restart grafana-server.service
SCRIPT

$vm_cpus = ENV["VM_CPUS"] || 2
$vm_memory = ENV["VM_MEMORY"] || 4096

Vagrant.configure("2") do |config|
  config.vm.define "terranet-dev" do |t|
    t.vm.box = "butja/terranet-base"
    t.vm.provider :virtualbox
    # Forward grafana interface
    t.vm.network "forwarded_port", guest: 3000, host: 3000
    # Forward influxdb port
    t.vm.network "forwarded_port", guest: 8086, host: 8086
    t.vm.provider "virtualbox" do |v|
        v.cpus = $vm_cpus
        v.memory = $vm_memory
    end
    t.vm.synced_folder "etc/collectd",
                       "/etc/collectd"
    t.vm.synced_folder "var/lib/collectd/python",
                       "/var/lib/collectd/python"
    t.vm.synced_folder "etc/influxdb",
                       "/etc/influxdb"
    t.vm.synced_folder "etc/grafana/provisioning/dashboards",
                       "/etc/grafana/provisioning/dashboards"
    t.vm.synced_folder "etc/grafana/provisioning/datasources",
                       "/etc/grafana/provisioning/datasources"
    t.vm.synced_folder "var/lib/grafana/dashboards",
                       "/var/lib/grafana/dashboards"
    t.vm.provision "shell", inline: $dev_provisioning
  end
end
