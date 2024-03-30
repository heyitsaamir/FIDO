Based off of https://github.com/ishan0102/vimGPT

# To run
```
sh setup.sh

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Modifications to make to run this

### env file
```
OPENAI_API_KEY=
PWDEBUG=1
```
`PWDDEBUG` launches playwright in debug mode so we can inspect the selectors (for the playbook). If you don't set this value, playbook recording features won't work (and that's ok)

### Browser modifications
The vimium extension has this custom mapping:
```
unmap r
```
Open the extension options and exclude it. It refreshes the browser if the agent types in `r`, which is not what we want.
