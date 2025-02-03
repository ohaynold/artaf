# Don't bother running this "script" from the shell; it's pointless. It must be source'd.
# Why: When you source a file within an executing script, it only affects the environment
#      within the scope of that executing script. It has no persistent effect on the shell.
# This gets source'd in 'install.sh' and 'runme.sh'

[[ -d "venv/bin" ]] && . venv/bin/activate
# Windows Python names the directory "Scripts"
# https://stackoverflow.com/questions/43826134/why-is-the-bin-directory-named-differently-scripts-on-windows
[[ -d "venv/Scripts" ]] && . venv/Scripts/activate