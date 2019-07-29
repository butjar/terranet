## Example
```bash
mkdir cfg out
python tn.py generate --cfg_dir=cfg network.json 
python tn.py simulate --cfg_dir=cfg --out_dir=out --time=2  # This will take a while
python tn.py run --cfg_path=cfg --out_path=out 

```