# vi: syntax=ruby
# vi: filetype=ruby

Vagrant.configure("2") do |config|
  config.vm.define "terranet-dev" do |t|
    t.vm.box = "butja/terranet-base"
    t.vm.provider :virtualbox
    # Forward grafana interface
    t.vm.network "forwarded_port", guest: 3000, host: 3000
  end
end
