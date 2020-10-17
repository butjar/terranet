# vi: syntax=ruby
# vi: filetype=ruby

require_relative 'vagrant_aws_hotfix'

$dev_trigger = <<~SCRIPT
  systemctl restart collectd.service
  systemctl restart influxdb.service
  systemctl restart influxd.service
  systemctl restart grafana-server.service
  pip3 install -e /vagrant
  SCRIPT

Vagrant.configure('2') do |config|
  config.vagrant.plugins = ['vagrant-aws']

  # virtualbox provider settings
  config.vm.provider 'virtualbox' do |vb, override|
    vb.cpus = ENV['VM_CPUS'] || 2
    vb.memory = ENV['VM_MEMORY'] || 4096

    # Forward grafana interface
    override.vm.network 'forwarded_port', guest: 3000, host: 3000
    # Forward influxdb port
    override.vm.network 'forwarded_port', guest: 8086, host: 8086
  end

  # aws provider settings
  config.vm.provider 'aws' do |aws, override|
    aws.region = "eu-central-1" # atm AMIs are only available here
    aws.keypair_name = "X1 Carbon"
    aws.security_groups = ["terranet"]
    aws.access_key_id = ENV['AWS_ACCESS_KEY_ID']
    aws.secret_access_key = ENV['AWS_SECRET_ACCESS_KEY']
    aws.ami = IO.readlines('TERRANET_BASE_AMI', chomp: true).join
    aws.instance_type = 'm5.2xlarge'

    override.ssh.username = "ubuntu"
    override.ssh.private_key_path = "/home/butjar/.ssh/id_rsa"
    end

  # terranet
  config.vm.define 'terranet', primary: true do |t|
    t.vm.box = 'butja/terranet'
    t.vm.synced_folder '.', '/vagrant', disabled: true

    config.vm.provider 'virtualbox' do |vb, override|
    # Forward grafana interface
    override.vm.network 'forwarded_port', guest: 3000, host: 3000
    # Forward influxdb port
    override.vm.network 'forwarded_port', guest: 8086, host: 8086
  end
  end

  # terranet dev
  config.vm.define 'terranet-dev', autostart: false  do |t|
    t.vm.box = 'butja/terranet-base'

    t.vm.provider 'aws' do |aws, override|
        override.vm.synced_folder '.', '/vagrant', type: 'rsync',
            rsync__exclude: ['.git/', 'vagrant/', 'build']
        override.vm.synced_folder 'etc/collectd',
                                  '/etc/collectd',
                                  type: 'rsync'
        override.vm.synced_folder 'var/lib/collectd/python',
                                  '/var/lib/collectd/python',
                                  type: 'rsync'
        override.vm.synced_folder 'etc/influxdb',
                                  '/etc/influxdb',
                                  type: 'rsync'
        override.vm.synced_folder 'etc/grafana/provisioning/dashboards',
                                  '/etc/grafana/provisioning/dashboards',
                                  type: 'rsync'
        override.vm.synced_folder 'etc/grafana/provisioning/datasources',
                                  '/etc/grafana/provisioning/datasources',
                                  type: 'rsync'
        override.vm.synced_folder 'var/lib/grafana/dashboards',
                                  '/var/lib/grafana/dashboards',
                                  type: 'rsync'
    end

    t.vm.provider 'virtualbox' do |vb, override|
      # Forward grafana interface
      override.vm.network 'forwarded_port', guest: 3000, host: 3030
      # Forward influxdb port
      override.vm.network 'forwarded_port', guest: 8086, host: 8886

      override.vm.synced_folder 'etc/collectd',
                                '/etc/collectd'
      override.vm.synced_folder 'var/lib/collectd/python',
                                '/var/lib/collectd/python'
      override.vm.synced_folder 'etc/influxdb',
                                '/etc/influxdb'
      override.vm.synced_folder 'etc/grafana/provisioning/dashboards',
                                '/etc/grafana/provisioning/dashboards'
      override.vm.synced_folder 'etc/grafana/provisioning/datasources',
                                '/etc/grafana/provisioning/datasources'
      override.vm.synced_folder 'var/lib/grafana/dashboards',
                                '/var/lib/grafana/dashboards'
    end

    t.vm.provision 'shell', inline:<<~SCRIPT
      influx -execute 'CREATE DATABASE customerstats'
      influx -execute 'CREATE DATABASE switchstats'
    SCRIPT

    t.trigger.after :up, :reload do |trigger|
        trigger.run_remote = { inline: $dev_trigger }
    end
  end
end
