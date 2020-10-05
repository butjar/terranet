# vi: syntax=ruby
# vi: filetype=ruby

# Variables
$vm_cpus = ENV['VM_CPUS'] || 2
$vm_memory = ENV['VM_MEMORY'] || 4096

# terranet-dev provisioning script
$dev_provisioning = <<~SCRIPT
  influx -execute 'CREATE DATABASE customerstats'
  influx -execute 'CREATE DATABASE switchstats'
SCRIPT

# terranet-dev after up trigger
$dev_init = <<~SCRIPT
  systemctl restart collectd.service
  systemctl restart influxdb.service
  systemctl restart influxd.service
  systemctl restart grafana-server.service

  pip3 install -e /vagrant
SCRIPT

Vagrant.configure('2') do |config|
  config.vm.provider 'virtualbox' do |v|
        v.cpus = $vm_cpus
        v.memory = $vm_memory
  end

  config.vm.define 'terranet', primary: true do |t|
    t.vm.box = 'butja/terranet'
    t.vm.synced_folder '.', '/vagrant', disabled: true
    # Forward grafana interface
    t.vm.network 'forwarded_port', guest: 3000, host: 3000
    # Forward influxdb port
    t.vm.network 'forwarded_port', guest: 8086, host: 8086
  end

  config.vm.define 'terranet-dev', autostart: false  do |t|
    t.vm.box = 'butja/terranet-base'
    # Forward grafana interface
    t.vm.network 'forwarded_port', guest: 3000, host: 3030
    # Forward influxdb port
    t.vm.network 'forwarded_port', guest: 8086, host: 8886
    t.vm.synced_folder 'etc/collectd',
                       '/etc/collectd'
    t.vm.synced_folder 'var/lib/collectd/python',
                       '/var/lib/collectd/python'
    t.vm.synced_folder 'etc/influxdb',
                       '/etc/influxdb'
    t.vm.synced_folder 'etc/grafana/provisioning/dashboards',
                       '/etc/grafana/provisioning/dashboards'
    t.vm.synced_folder 'etc/grafana/provisioning/datasources',
                       '/etc/grafana/provisioning/datasources'
    t.vm.synced_folder 'var/lib/grafana/dashboards',
                       '/var/lib/grafana/dashboards'
    t.vm.provision 'shell', inline: $dev_provisioning

    t.trigger.after :up, :reload do |trigger|
        trigger.run_remote = { inline: $dev_init }
    end
  end
end
