Set WshShell = CreateObject("WScript.Shell")
' Force the script to execute in the workspace directory
WshShell.CurrentDirectory = "E:\Deb\Friday"
' Run the python daemon silently (0 indicates hidden window)
WshShell.Run "python headless_friday.py", 0, False
