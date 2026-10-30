# Session and shell lifecycle regression tests

Run from the repository root on a POSIX system with Python 3 (validated with Python 3.10.5):

```sh
python3 -B tests/test_shell_lifecycle.py
```

The suite uses only the standard library. It compiles the actual class and
method bodies from `core/agent.py` and `app_shell/shell.py` using `ast`, replacing
network, native libraries and service bootstrap with small fakes. No agent is
installed or started, no configuration is read, and no DWService account or
network connection is needed. This allows testing cleanup and lock ordering
without compiling the native agent dependencies.

The 33 tests cover callback lock inversion, concurrent open/close and idle app
unloading, update waits, duplicate and stale closes, bounded nonblocking reaping,
PTY descriptor ownership, partial initialization, signal guards, and a lazy
reaper shared across app reloads. The two registry stress tests exercise 650
session lifecycles while checking callback uniqueness and/or heartbeat progress.
Injected OS failures never signal real PIDs.

Five integration tests create real `/bin/sh` PTYs and child processes on macOS;
they are skipped elsewhere. They check immediate open/close (30 cycles), normal
foreground jobs, inherited ignored SIGTERM, foreground jobs ignoring both HUP
and TERM, and a direct child ignoring TERM. They assert process disappearance
before emergency cleanup and check descriptor/activity counts. Child shells use
a temporary HOME. Run in a disposable test environment: these tests create and
signal their own children, and use `ps` to observe them. The same suite can be run
as root there to exercise the service's privilege context.

`DWAGENT_TEST_SOURCE` can point to a different repository checkout for negative
controls. These four tests fail on the unmodified base and pass with the fix:

- `LifecycleTests.test_callback_releases_global_lock_and_remains_registered`
- `ProcessTests.test_bounded_wait_and_eventual_reap`
- `ProcessTests.test_pty_master_closed_after_one_termination`
- `ProcessTests.test_initialization_failure_closes_owned_fd`

These are isolated lifecycle tests, not a full distribution/bootstrap test or
proof that every descendant (for example, a daemonized background job) is killed.
Windows terminal cleanup is not exercised by this suite.
