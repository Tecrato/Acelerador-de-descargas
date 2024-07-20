@echo off
set PUERTO=5000

FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :%PUERTO%') DO taskkill /F /PID %%P
