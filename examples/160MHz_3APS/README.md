## Example
```bash
mkdir cfg out
terranet generate --cfg_dir=cfg network.json 
terranet simulate --cfg_dir=cfg --out_dir=out --time=2  # This will take a while
sudo terranet run --cfg_path=cfg --out_path=out  # sudo required for mininet 
```
In this example we first generate configurations for komondor using the basic topology defined in
 `network.json`: Three backhaul APs arranged in a line each with three, one and two client nodes associated, respectively. 

Afterwards we simulate the whole configuration space for 2 seconds and save the results in the `out` folder. 
In the last step we emulate the wireless network using ipmininet and parameterize the links using the results in `out` for
a given configuration in `cfg`. 