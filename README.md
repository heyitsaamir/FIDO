Based off of https://github.com/ishan0102/vimGPT

## Modifications to make to run this

### env file
```
OPENAI_API_KEY=
PWDEBUG=1
```
PWDDEBUG launches playwright in debug mode so we can inspect the selectors (for the playbook)

### Browser modifications
The vimium extension has this custom mapping:
```
map X LinkHints.activateMode action=focus
```
Open the extension options and include it. It's used for playback recording.