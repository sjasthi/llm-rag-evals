import msvcrt
"""
Windows Job Object supervisor for RAG evaluation subprocesses.

Foundation: verified ctypes structures and Windows API declarations.
Process execution and lifecycle management will be added separately.
"""
import ctypes
import os
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        (name, ctypes.c_ulonglong)
        for name in (
            "ReadOperationCount", "WriteOperationCount",
            "OtherOperationCount", "ReadTransferCount",
            "WriteTransferCount", "OtherTransferCount"
        )
    ]

class BASIC_LIMIT(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]

class EXTENDED_LIMIT(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", BASIC_LIMIT),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]

class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]

kernel32.CreateJobObjectW.argtypes = [
    ctypes.c_void_p, wintypes.LPCWSTR
]
kernel32.CreateJobObjectW.restype = wintypes.HANDLE

kernel32.SetInformationJobObject.argtypes = [
    wintypes.HANDLE, ctypes.c_int,
    ctypes.c_void_p, wintypes.DWORD
]
kernel32.SetInformationJobObject.restype = wintypes.BOOL

kernel32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR, wintypes.LPWSTR,
    ctypes.c_void_p, ctypes.c_void_p,
    wintypes.BOOL, wintypes.DWORD,
    ctypes.c_void_p, wintypes.LPCWSTR,
    ctypes.POINTER(STARTUPINFOW),
    ctypes.POINTER(PROCESS_INFORMATION),
]
kernel32.CreateProcessW.restype = wintypes.BOOL

# Accept either STARTUPINFOW or STARTUPINFOEXW.
# The caller supplies the correctly initialized structure.
_create_process_argtypes = list(kernel32.CreateProcessW.argtypes)
_create_process_argtypes[8] = ctypes.c_void_p
kernel32.CreateProcessW.argtypes = _create_process_argtypes

kernel32.AssignProcessToJobObject.argtypes = [
    wintypes.HANDLE, wintypes.HANDLE
]
kernel32.AssignProcessToJobObject.restype = wintypes.BOOL

kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
kernel32.ResumeThread.restype = wintypes.DWORD

kernel32.WaitForSingleObject.argtypes = [
    wintypes.HANDLE, wintypes.DWORD
]
kernel32.WaitForSingleObject.restype = wintypes.DWORD

kernel32.TerminateProcess.argtypes = [
    wintypes.HANDLE, wintypes.UINT
]
kernel32.TerminateProcess.restype = wintypes.BOOL

kernel32.OpenProcess.argtypes = [
    wintypes.DWORD, wintypes.BOOL, wintypes.DWORD
]
kernel32.OpenProcess.restype = wintypes.HANDLE

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

# Process monitoring constants.
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
INFINITE = 0xFFFFFFFF
STILL_ACTIVE = 259

CREATE_SUSPENDED = 0x00000004
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9

# Retrieve the actual exit code of a supervised process.
kernel32.GetExitCodeProcess.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.GetExitCodeProcess.restype = wintypes.BOOL

def create_kill_on_close_job():
    """Create a Windows Job Object that terminates members on closure."""
    job = kernel32.CreateJobObjectW(None, None)

    if not job:
        raise ctypes.WinError(ctypes.get_last_error())

    try:
        limits = EXTENDED_LIMIT()
        limits.BasicLimitInformation.LimitFlags = (
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        )

        configured = kernel32.SetInformationJobObject(
            job,
            JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(limits),
            ctypes.sizeof(limits),
        )

        if not configured:
            raise ctypes.WinError(ctypes.get_last_error())

        return job

    except BaseException:
        kernel32.CloseHandle(job)
        raise

def create_suspended_process(
    command,
    working_directory=None,
    stdin_handle=None,
    stdout_handle=None,
    stderr_handle=None,
):
    """Create a suspended process with optional redirected standard handles."""
    if not command:
        raise ValueError("Subprocess command cannot be empty.")

    command = [os.fspath(arg) for arg in command]
    command_line = subprocess.list2cmdline(command)

    startup = STARTUPINFOW()
    startup.cb = ctypes.sizeof(startup)

    handles = (stdin_handle, stdout_handle, stderr_handle)
    redirected = any(handle is not None for handle in handles)

    if redirected and not all(handle is not None for handle in handles):
        raise ValueError("All three standard handles are required for redirection.")

    if redirected:
        startup.dwFlags |= STARTF_USESTDHANDLES
        startup.hStdInput = stdin_handle
        startup.hStdOutput = stdout_handle
        startup.hStdError = stderr_handle

    info = PROCESS_INFORMATION()

    if not redirected:
        created = kernel32.CreateProcessW(
            command[0],
            ctypes.create_unicode_buffer(command_line),
            None,
            None,
            False,
            CREATE_SUSPENDED,
            None,
            working_directory,
            ctypes.byref(startup),
            ctypes.byref(info),
        )

        if not created:
            raise ctypes.WinError(ctypes.get_last_error())

        return info

    # Preserve existing inheritance flags for all three handles.
    handles = [int(handle) for handle in handles]
    original_flags = {}
    attributes = None

    try:
        for handle in handles:
            flags = wintypes.DWORD()

            if not kernel32.GetHandleInformation(
                handle, ctypes.byref(flags)
            ):
                raise ctypes.WinError(ctypes.get_last_error())

            original_flags[handle] = flags.value

        for handle in handles:
            if not kernel32.SetHandleInformation(
                handle,
                HANDLE_FLAG_INHERIT,
                HANDLE_FLAG_INHERIT,
            ):
                raise ctypes.WinError(ctypes.get_last_error())

        attributes = create_restricted_handle_list(handles)

        extended = STARTUPINFOEXW()
        extended.StartupInfo = startup
        extended.StartupInfo.cb = ctypes.sizeof(extended)
        extended.lpAttributeList = attributes["attribute_list"]

        created = kernel32.CreateProcessW(
            command[0],
            ctypes.create_unicode_buffer(command_line),
            None,
            None,
            True,
            CREATE_SUSPENDED | EXTENDED_STARTUPINFO_PRESENT,
            None,
            working_directory,
            ctypes.byref(extended),
            ctypes.byref(info),
        )

        if not created:
            raise ctypes.WinError(ctypes.get_last_error())

        return info

    except BaseException:
        if info.hProcess:
            try:
                kernel32.TerminateProcess(info.hProcess, 1)
                kernel32.WaitForSingleObject(info.hProcess, 5000)
            finally:
                close_process_handles(info)
        raise

    finally:
        cleanup_error = None

        try:
            if attributes is not None:
                close_restricted_handle_list(attributes)
        except BaseException as exc:
            cleanup_error = exc

        for handle, flags in original_flags.items():
            if not kernel32.SetHandleInformation(
                handle,
                HANDLE_FLAG_INHERIT,
                flags & HANDLE_FLAG_INHERIT,
            ):
                if cleanup_error is None:
                    cleanup_error = ctypes.WinError(ctypes.get_last_error())

        if cleanup_error is not None:
            if info.hProcess:
                try:
                    kernel32.TerminateProcess(info.hProcess, 1)
                    kernel32.WaitForSingleObject(info.hProcess, 5000)
                finally:
                    close_process_handles(info)

            if sys.exc_info()[0] is None:
                raise cleanup_error

def assign_and_resume_process(job, info):
    """Assign a suspended process to a Job Object, then resume it."""
    try:
        assigned = kernel32.AssignProcessToJobObject(
            job,
            info.hProcess,
        )

        if not assigned:
            raise ctypes.WinError(ctypes.get_last_error())

        result = kernel32.ResumeThread(info.hThread)

        if result == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())

    except BaseException:
        kernel32.TerminateProcess(info.hProcess, 1)
        kernel32.WaitForSingleObject(info.hProcess, 5000)
        raise

def close_process_handles(info):
    """Close process and thread handles after execution or failure."""
    if info is None:
        return

    if info.hThread:
        kernel32.CloseHandle(info.hThread)
        info.hThread = None

    if info.hProcess:
        kernel32.CloseHandle(info.hProcess)
        info.hProcess = None

def wait_for_process_exit(info, timeout_ms=INFINITE):
    """Wait for process completion and return its exit code."""
    result = kernel32.WaitForSingleObject(
        info.hProcess,
        timeout_ms,
    )

    if result == WAIT_TIMEOUT:
        return None

    if result != WAIT_OBJECT_0:
        raise ctypes.WinError(ctypes.get_last_error())

    exit_code = wintypes.DWORD()

    if not kernel32.GetExitCodeProcess(
        info.hProcess,
        ctypes.byref(exit_code),
    ):
        raise ctypes.WinError(ctypes.get_last_error())

    return exit_code.value

def close_job_object(job):
    """Close the Job Object, terminating remaining member processes."""
    if not job:
        return

    if not kernel32.CloseHandle(job):
        raise ctypes.WinError(ctypes.get_last_error())

def cleanup_supervised_process(job, info):
    """Release the Job Object and process handles safely."""
    try:
        if job:
            close_job_object(job)
    finally:
        close_process_handles(info)

def verify_process_stopped(info, timeout_ms=5000):
    """Verify that the tracked process has exited within the timeout."""
    if info is None or not info.hProcess:
        raise ValueError("A valid process handle is required.")

    result = kernel32.WaitForSingleObject(
        info.hProcess,
        timeout_ms,
    )

    if result == WAIT_OBJECT_0:
        return True

    if result == WAIT_TIMEOUT:
        return False

    raise ctypes.WinError(ctypes.get_last_error())

# Windows Job Object basic accounting information.
JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION = 1


class JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("TotalUserTime", ctypes.c_longlong),
        ("TotalKernelTime", ctypes.c_longlong),
        ("ThisPeriodTotalUserTime", ctypes.c_longlong),
        ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
        ("TotalPageFaultCount", wintypes.DWORD),
        ("TotalProcesses", wintypes.DWORD),
        ("ActiveProcesses", wintypes.DWORD),
        ("TotalTerminatedProcesses", wintypes.DWORD),
    ]


kernel32.QueryInformationJobObject.argtypes = [
    wintypes.HANDLE,
    ctypes.c_int,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryInformationJobObject.restype = wintypes.BOOL

def get_job_active_process_count(job):
    """Return the number of active processes in a Windows Job Object."""
    if not job:
        raise ValueError("A valid Job Object handle is required.")

    accounting = JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
    returned_length = wintypes.DWORD()

    success = kernel32.QueryInformationJobObject(
        job,
        JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION,
        ctypes.byref(accounting),
        ctypes.sizeof(accounting),
        ctypes.byref(returned_length),
    )

    if not success:
        raise ctypes.WinError(ctypes.get_last_error())

    return int(accounting.ActiveProcesses)

def wait_for_job_completion(job, timeout_seconds, poll_interval=0.1):
    """Wait until all Job Object processes exit, with a timeout."""
    if timeout_seconds <= 0:
        raise ValueError("Timeout must be positive.")

    if poll_interval <= 0:
        raise ValueError("Polling interval must be positive.")

    deadline = time.monotonic() + timeout_seconds

    while True:
        active_count = get_job_active_process_count(job)

        if active_count == 0:
            return True

        remaining = deadline - time.monotonic()

        if remaining <= 0:
            return False

        time.sleep(min(poll_interval, remaining))

# Windows standard-handle configuration for redirected child output.
STARTF_USESTDHANDLES = 0x00000100

kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
kernel32.GetStdHandle.restype = wintypes.HANDLE

kernel32.SetHandleInformation.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.DWORD,
]
kernel32.SetHandleInformation.restype = wintypes.BOOL

HANDLE_FLAG_INHERIT = 0x00000001

STD_INPUT_HANDLE = 0xFFFFFFF6
STD_OUTPUT_HANDLE = 0xFFFFFFF5
STD_ERROR_HANDLE = 0xFFFFFFF4

def open_redirected_output_files(stdout_path, stderr_path):
    """Open binary output files and obtain their Windows handles."""
    stdout_file = None
    stderr_file = None

    try:
        stdout_file = open(stdout_path, "wb")
        stderr_file = open(stderr_path, "wb")

        stdout_handle = msvcrt.get_osfhandle(stdout_file.fileno())
        stderr_handle = msvcrt.get_osfhandle(stderr_file.fileno())

        return {
            "stdout_file": stdout_file,
            "stderr_file": stderr_file,
            "stdout_handle": stdout_handle,
            "stderr_handle": stderr_handle,
        }

    except BaseException:
        if stderr_file is not None:
            stderr_file.close()

        if stdout_file is not None:
            stdout_file.close()

        raise

def close_redirected_output_files(output):
    """Close redirected stdout and stderr files safely."""
    if not output:
        return

    first_error = None

    for key in ("stderr_file", "stdout_file"):
        file_object = output.get(key)

        if file_object is not None and not file_object.closed:
            try:
                file_object.close()
            except OSError as exc:
                if first_error is None:
                    first_error = exc

    if first_error is not None:
        raise first_error

def set_output_handle_inheritance(output, inheritable):
    """Configure inheritance for redirected output handles."""
    if not output:
        raise ValueError("Output handles are required.")

    flags = HANDLE_FLAG_INHERIT if inheritable else 0

    for key in ("stdout_handle", "stderr_handle"):
        handle = output[key]

        success = kernel32.SetHandleInformation(
            handle,
            HANDLE_FLAG_INHERIT,
            flags,
        )

        if not success:
            raise ctypes.WinError(ctypes.get_last_error())

def open_redirected_stdin():
    """Open Windows NUL as a non-interactive stdin stream."""
    stdin_file = open(os.devnull, "rb")

    try:
        stdin_handle = msvcrt.get_osfhandle(stdin_file.fileno())

        return {
            "stdin_file": stdin_file,
            "stdin_handle": stdin_handle,
        }

    except BaseException:
        stdin_file.close()
        raise

def close_redirected_stdin(stdin):
    """Close the non-interactive stdin file safely."""
    if not stdin:
        return

    stdin_file = stdin.get("stdin_file")

    if stdin_file is not None and not stdin_file.closed:
        stdin_file.close()

# Windows extended startup information for restricted handle inheritance.
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x00020002


class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [
        ("StartupInfo", STARTUPINFOW),
        ("lpAttributeList", ctypes.c_void_p),
    ]


kernel32.InitializeProcThreadAttributeList.argtypes = [
    ctypes.c_void_p,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.InitializeProcThreadAttributeList.restype = wintypes.BOOL

kernel32.UpdateProcThreadAttribute.argtypes = [
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.c_size_t,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_void_p,
    ctypes.c_void_p,
]
kernel32.UpdateProcThreadAttribute.restype = wintypes.BOOL

kernel32.DeleteProcThreadAttributeList.argtypes = [
    ctypes.c_void_p,
]
kernel32.DeleteProcThreadAttributeList.restype = None

def create_restricted_handle_list(handles):
    """Create a Windows process attribute list for selected handles."""
    if not handles:
        raise ValueError("At least one handle is required.")

    handles = [int(handle) for handle in handles]

    if any(handle <= 0 for handle in handles):
        raise ValueError("All handles must be valid positive values.")

    size = ctypes.c_size_t()

    # First call determines the required attribute-list buffer size.
    kernel32.InitializeProcThreadAttributeList(
        None, 1, 0, ctypes.byref(size)
    )

    if size.value == 0:
        raise ctypes.WinError(ctypes.get_last_error())

    buffer = ctypes.create_string_buffer(size.value)
    attribute_list = ctypes.cast(buffer, ctypes.c_void_p)

    initialized = kernel32.InitializeProcThreadAttributeList(
        attribute_list, 1, 0, ctypes.byref(size)
    )

    if not initialized:
        raise ctypes.WinError(ctypes.get_last_error())

    try:
        handle_array = (wintypes.HANDLE * len(handles))(*handles)

        updated = kernel32.UpdateProcThreadAttribute(
            attribute_list,
            0,
            PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
            ctypes.cast(handle_array, ctypes.c_void_p),
            ctypes.sizeof(handle_array),
            None,
            None,
        )

        if not updated:
            raise ctypes.WinError(ctypes.get_last_error())

        return {
            "buffer": buffer,
            "attribute_list": attribute_list,
            "handle_array": handle_array,
        }

    except BaseException:
        kernel32.DeleteProcThreadAttributeList(attribute_list)
        raise

def close_restricted_handle_list(attributes):
    """Release an initialized Windows process attribute list."""
    if not attributes:
        return

    attribute_list = attributes.get("attribute_list")

    if attribute_list:
        kernel32.DeleteProcThreadAttributeList(attribute_list)
        attributes["attribute_list"] = None

kernel32.GetHandleInformation.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.GetHandleInformation.restype = wintypes.BOOL


def run_supervised_command(command, timeout_seconds, working_directory=None):
    """Run a command under a kill-on-close Windows Job Object."""
    if timeout_seconds <= 0:
        raise ValueError("Timeout must be positive.")

    job = None
    info = None
    output = None
    stdin = None
    timed_out = False
    exit_code = None

    with tempfile.TemporaryDirectory(prefix="rag_supervised_") as folder:
        stdout_path = os.path.join(folder, "stdout.txt")
        stderr_path = os.path.join(folder, "stderr.txt")

        try:
            output = open_redirected_output_files(
                stdout_path, stderr_path
            )
            stdin = open_redirected_stdin()

            job = create_kill_on_close_job()

            info = create_suspended_process(
                command,
                working_directory=working_directory,
                stdin_handle=stdin["stdin_handle"],
                stdout_handle=output["stdout_handle"],
                stderr_handle=output["stderr_handle"],
            )

            assign_and_resume_process(job, info)

            completed = wait_for_job_completion(
                job, timeout_seconds
            )

            timed_out = not completed

            if completed:
                code = wintypes.DWORD()

                if not kernel32.GetExitCodeProcess(
                    info.hProcess, ctypes.byref(code)
                ):
                    raise ctypes.WinError(ctypes.get_last_error())

                exit_code = code.value

        finally:
            try:
                if job is not None:
                    close_job_object(job)
                    job = None
            finally:
                try:
                    if info is not None and info.hProcess:
                        close_process_handles(info)
                finally:
                    try:
                        if stdin is not None:
                            close_redirected_stdin(stdin)
                    finally:
                        if output is not None:
                            close_redirected_output_files(output)

        stdout_text = evaluation_read_text(stdout_path)
        stderr_text = evaluation_read_text(stderr_path)

        return {
            "timed_out": timed_out,
            "exit_code": exit_code,
            "stdout": stdout_text,
            "stderr": stderr_text,
        }


def evaluation_read_text(path, max_bytes=1048576):
    """Read subprocess output; reject files exceeding the size limit."""
    if max_bytes <= 0:
        raise ValueError("Output size limit must be positive.")

    with open(path, "rb") as stream:
        data = stream.read(max_bytes + 1)

    if len(data) > max_bytes:
        raise ValueError("Subprocess output exceeded the capture limit.")

    return data.decode("utf-8", errors="replace")


def main():
    """Execute one JSON-described command and print its result as JSON."""
    import json

    if len(sys.argv) != 2:
        print(
            json.dumps({
                "supervisor_ok": False,
                "error": "Expected one JSON request-file argument."
            })
        )
        return 2

    try:
        with open(sys.argv[1], "r", encoding="utf-8") as stream:
            request = json.load(stream)

        if not isinstance(request, dict):
            raise ValueError("Request must be a JSON object.")

        command = request.get("command")
        timeout_seconds = request.get("timeout_seconds")
        working_directory = request.get("working_directory")

        if (
            not isinstance(command, list)
            or not command
            or not all(
                isinstance(value, str) and value
                for value in command
            )
        ):
            raise ValueError("Command must be a nonempty string array.")

        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not 0 < timeout_seconds <= 3600
        ):
            raise ValueError(
                "Timeout must be between 0 and 3600 seconds."
            )

        if (
            working_directory is not None
            and not isinstance(working_directory, str)
        ):
            raise ValueError(
                "Working directory must be a string or null."
            )

        result = run_supervised_command(
            command,
            timeout_seconds,
            working_directory=working_directory,
        )

        print(json.dumps({
            "supervisor_ok": True,
            **result,
        }))

        return 0

    except Exception as exc:
        print(json.dumps({
            "supervisor_ok": False,
            "error": type(exc).__name__,
        }))
        return 1


if __name__ == "__main__":
    sys.exit(main())
