#include "stdlib.h"
#include "stdio.h"
#include <process.h>
#include <Windows.h>
#include <assert.h>
int wmain(int argc, wchar_t *argv[], wchar_t *envp) {
#ifdef DEBUG_VERSION
	SetEnvironmentVariableW(L"PYCALL_JULIA_FLAVOR",L"julia-debug");
#else
	SetEnvironmentVariableW(L"PYCALL_JULIA_FLAVOR",L"julia");
#endif
	SetEnvironmentVariableW(L"JULIA_HOME",_wgetenv(L"PYCALL_JULIA_HOME"));
	wchar_t *python_process = _wgetenv(L"PYCALL_PYTHON_EXE");
	if (python_process == NULL)
		python_process = L"python";
	const wchar_t ** new_argv = malloc(sizeof(wchar_t*)*(argc+3));
	new_argv[0] = python_process;
	// Determine location of the executable and replace .exe by .py
	wchar_t *exe_path = malloc(260 * sizeof(wchar_t));
	DWORD path_len = GetModuleFileNameW(NULL, exe_path, 260);
	if (path_len == 0)
		abort();
#ifdef DEBUG_VERSION
	int strip_len = 9;
#else
	int strip_len = 3;
#endif
	exe_path[path_len - strip_len] = L'p';
	exe_path[path_len - strip_len + 1] = L'y';
	exe_path[path_len - strip_len + 2] = L'\0';
	new_argv[1] = exe_path;
	new_argv[2] = L"--";
	for (int i = 1; i < argc; ++i) {
		// Add extra quotes so python's argument parsing doesn't
		// mess up the arguments for us
		size_t strLen = wcslen(argv[i]);
		size_t bufferLen = strLen + 3;
		wchar_t *new_buf = malloc(bufferLen*sizeof(wchar_t));
		memcpy(new_buf+1, argv[i], strLen*sizeof(wchar_t));
		new_buf[0] = L'"';
		new_buf[bufferLen - 2] = L'"';
		new_buf[bufferLen - 1] = L'\0';
		//printf("%d: %ls\n", i, new_buf);
		new_argv[i+2] = new_buf;
	}
	new_argv[2+argc] = NULL;
	intptr_t exit = _wspawnvp(_P_WAIT, python_process, new_argv);
	return exit;
}