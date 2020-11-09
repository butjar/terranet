Vagrant.configure("2") do |config|
  config.vm.define "source", autostart: false do |source|
	source.vm.box = "{{.SourceBox}}"
    source.vm.provider "virtualbox" do |v|
        v.cpus = 2
        v.memory = 5120
    end
    source.vagrant.plugins = ["vagrant-disksize"]
    source.disksize.size = "15GB"
	config.ssh.insert_key = {{.InsertKey}}
  end
  config.vm.define "output" do |output|
    output.vm.provider "virtualbox"
	output.vm.box = "{{.BoxName}}"
	output.vm.box_url = "file://package.box"
	config.ssh.insert_key = {{.InsertKey}}
  end
  {{ if ne .SyncedFolder "" -}}
  config.vm.synced_folder "{{.SyncedFolder}}", "/vagrant"
  {{- else -}}
  config.vm.synced_folder ".", "/vagrant", disabled: true
  {{- end}}
end
