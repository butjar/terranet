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
Vagrant.configure("2") do |config|
  config.vm.define "terranet-dev" do |t|
    t.vm.box = "butja/terranet-base"
    t.vm.provider :virtualbox
    # Forward grafana interface
    t.vm.network "forwarded_port", guest: 3000, host: 3000
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
