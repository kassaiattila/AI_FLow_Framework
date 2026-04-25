@echo off
REM AIFlow stack startup — Windows wrapper for scripts/start_stack.sh
REM Requires Git Bash (comes with Git for Windows) or WSL.
REM
REM Usage: scripts\start_stack.cmd [flags...]
REM   Examples:
REM     scripts\start_stack.cmd
REM     scripts\start_stack.cmd --with-api --with-ui
REM     scripts\start_stack.cmd --full
REM     scripts\start_stack.cmd --down

setlocal
set SCRIPT_DIR=%~dp0
set BASH_EXE=

REM Try common Git Bash locations
if exist "C:\Program Files\Git\bin\bash.exe" set BASH_EXE=C:\Program Files\Git\bin\bash.exe
if exist "C:\Program Files (x86)\Git\bin\bash.exe" set BASH_EXE=C:\Program Files (x86)\Git\bin\bash.exe

if "%BASH_EXE%"=="" (
    where bash >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set BASH_EXE=bash
    ) else (
        echo [FAIL] bash not found. Install Git for Windows: https://git-scm.com/download/win
        exit /b 1
    )
)

"%BASH_EXE%" "%SCRIPT_DIR%start_stack.sh" %*
