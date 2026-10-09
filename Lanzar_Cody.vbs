' Lanzar_Cody.vbs - Ejecuta Cody.exe silenciosamente
Option Explicit
Dim fso, shell, carpeta, rutaExe
Set fso   = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
carpeta  = fso.GetParentFolderName(WScript.ScriptFullName)
rutaExe  = carpeta & "\Cody.exe"
If Not fso.FileExists(rutaExe) Then WScript.Quit 1
shell.CurrentDirectory = carpeta
shell.Run """" & rutaExe & """", 0, False
WScript.Quit 0