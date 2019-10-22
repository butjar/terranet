## Example
```bash
mkdir cfg out
terranet generate --cfg_dir=cfg network.json 
terranet simulate --cfg_dir=cfg --out_dir=out --time=2  # This will take a while
sudo terranet run network.json --cfg_path=cfg --out_path=out  # sudo required for mininet 
```
In this example we first generate configurations for komondor using the basic topology defined in
 `network.json`: Three backhaul APs arranged in a line each with three, one and two client nodes associated, respectively. 

Afterwards we simulate the whole configuration space for 2 seconds and save the results in the `out` folder. 
In the last step we emulate the wireless network using ipmininet and parameterize the links using the results in `out` for
a given configuration in `cfg`. 

### Visualization
To visualize the running network you can install the `terranet-dashboard` snap, which shows current flow rates as well 
as the topology of the network in a NodeRed dashboard:
```bash
sudo snap install terranet-dashboard
terranet-dashboard
# Open your browser on https://localhost:1880/ui
```

### Attaching a Controller
During emulation the channel configuration of the backhaul APs can be changed using a custom controller instance.
Simply write a Python file and in it implement a subclass of `TerraNetController` and load it using the CLI:
```console
mininet> ctrl_attach my_controller.py
``` 
Example controllers can be found in `dummy_ctrl.py` or `drunk_ctrl.py`. 
The controller files are loaded as a python module and the first subclass of `TerraNetController` that is found is instantiated and its `ctrl_loop()` method is executed in separate thread. 
The controller automatically runs in the correct namespace of the controller node.
