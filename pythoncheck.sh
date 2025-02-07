# This is used to determine the specific command required to launch python.
# In Windows python, the file is called "python.exe" and considerable workarounds are required to make "python3"
# a valid command. It's far easier to just use the native filename.

if type -P python &> /dev/null ; then
    python_command() {
        python "$@"
    }
elif type -P python3 &> /dev/null ; then
    python_command() {
        python3 "$@"
    }
else
    echo "There appears to be neither \"python3\" nor \"python\" in your PATH;"
    echo "you may need to reinstall Python or reboot your computer."
    exit
fi