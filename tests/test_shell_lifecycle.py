"""Regression tests using DWAgent method bodies from this checkout.

No service, credentials, network, installed files, or unrelated processes are
touched. Actual PTYs use a temporary HOME. Fake OS faults never signal real PIDs.
"""
import ast
import errno
import fcntl
import io
import itertools
import json
import os
from pathlib import Path
import pty
import pwd
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parent
SOURCE=Path(os.environ.get('DWAGENT_TEST_SOURCE',ROOT.parent))


class Counter:
    def __init__(self,limit=0): self.limit=limit;self.reset()
    def reset(self): self.start=time.monotonic()
    def is_elapsed(self,seconds=None): return time.monotonic()-self.start >= (self.limit if seconds is None else seconds)


def method(source, cls, name, env):
    tree=ast.parse(source.read_text())
    parent=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
    node=next(n for n in parent.body if isinstance(n,ast.FunctionDef) and n.name==name)
    local=dict(env)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),local)
    return local[name]


def load(os_api=os):
    utils=SimpleNamespace(Counter=Counter,get_exception=lambda:sys.exc_info()[1],
        exception_to_string=str,path_exists=os.path.exists,
        str_to_bytes=lambda s,enc='utf8':s.encode(enc),
        bytes_to_str=lambda s,enc='utf8':s.decode(enc,errors='replace'))
    platform=SimpleNamespace(is_windows=lambda:False,is_linux=lambda:False,is_mac=lambda:True,
                             generate_key=lambda n:os.urandom(n).hex())
    native=SimpleNamespace(get_instance=lambda:SimpleNamespace(get_utf8_lang=lambda:'en_US.UTF-8'))
    env=dict(threading=threading,time=time,os=os_api,errno=errno,signal=signal,utils=utils,
        io=io,sys=sys,struct=struct,json=json,fcntl=fcntl,pty=pty,termios=termios,
        agent=platform,native=native,subprocess=subprocess,
        SHELL_TIMEOUT_CONNECTION=40,SHELL_TIMEOUT_RECOVERY=20,SHELL_VERSION=1)
    shell_path=SOURCE/'app_shell/shell.py'
    tree=ast.parse(shell_path.read_text())
    nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))
           or isinstance(n,ast.Assign) and all(isinstance(t,ast.Name) and t.id.startswith('SHELL_') for t in n.targets)]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(shell_path),'exec'),env)
    agent_path=SOURCE/'core/agent.py'
    methods={name:method(agent_path,'Agent',name,env) for name in (
        '_fire_close_conn_apps','close_session','_close_all_sessions','get_active_sessions_status',
        '_unload_apps','_unload_app')}
    try: methods['_unload_apps_if_idle']=method(agent_path,'Agent','_unload_apps_if_idle',env)
    except StopIteration: pass
    class TestAgent:
        def __init__(self):
            self._sessions_semaphore=threading.Condition()
            self._libs_apps_semaphore=threading.Condition()
            self._sessions={};self._sessions_closing=set();self._sessions_update_status=''
            self._apps={};self.errors=[];self.infos=[]
        def write_except(self,error,*args): self.errors.append(str(error))
        def write_err(self,error): self.errors.append(str(error))
        def write_info(self,text): self.infos.append(text)
        def get_config(self,key,default=None): return False if key=='recovery_session' else default
        def get_proxy_info(self): return None
        def _get_sys_info(self): return {}
        def _get_agent_distr_id(self): return 65
    for name,fn in methods.items(): setattr(TestAgent,name,fn)
    class TestSession:
        def __init__(self,a,conn=None,sid='one',msg=None):
            self._agent=a;self.sid=sid;self._activities={'shellSession':0}
        def get_idsession(self): return self.sid
        def get_wait_accept(self): return False
        def get_password_request(self): return False
        def get_last_activity_time(self): return time.time()
        def get_init_time(self): return 0
        def get_access_type(self): return 'qa'
        def get_user_name(self): return 'qa'
        def get_ipaddress(self): return 'isolated'
        def close(self): self._agent.close_session(self)
    for name in ('inc_activities_value','dec_activities_value','get_activities'):
        setattr(TestSession,name,method(agent_path,'Session',name,env))
    class Connection:
        def __init__(self,*args): pass
        def close(self): pass
    counter=itertools.count()
    open_env=dict(env,Session=TestSession,Connection=Connection,generate_key=lambda n:'new-%s'%next(counter))
    TestAgent.open_session=method(agent_path,'Agent','open_session',open_env)
    return env,TestAgent,TestSession


def join(t,limit=2):
    t.join(limit)
    if t.is_alive(): raise AssertionError('thread did not finish: '+t.name)


def launch(fn,name='qa-worker'):
    errors=[]
    def run():
        try: fn()
        except BaseException as e: errors.append(e)
    t=threading.Thread(target=run,name=name);t.daemon=True;t.start()
    return t,errors


OPEN=dict(connectionTimeout=8,connServer='isolated',connPort=0,connInstance='qa',
          connVersion=1,connUser='qa',connPassword='not-a-credential')


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.env,A,self.Session=load();self.a=A()
    def add(self,sid='one'):
        s=self.Session(self.a,sid=sid);self.a._sessions[sid]=s;return s
    def app(self,callback=lambda sid:None,destroy=lambda force:True):
        p=SimpleNamespace(on_conn_close=callback,destroy=destroy)
        self.a._apps['test']=p;return p
    def test_callback_releases_global_lock_and_remains_registered(self):
        s=self.add();entered,release=threading.Event(),threading.Event()
        self.app(lambda sid:(entered.set(),release.wait(3)))
        t,errors=launch(lambda:self.a.close_session(s))
        try:
            self.assertTrue(entered.wait(1))
            got=self.a._sessions_semaphore.acquire(timeout=.15)
            self.assertTrue(got,'global sessions lock held during app callback')
            if got:
                try: self.assertIs(self.a._sessions['one'],s)
                finally: self.a._sessions_semaphore.release()
            status,errs=launch(self.a.get_active_sessions_status,'heartbeat')
            join(status,.3);self.assertFalse(errs)
        finally: release.set();join(t)
        self.assertFalse(errors);self.assertFalse(self.a._sessions)
    def test_lock_inversion_with_concurrent_shell_open(self):
        s=self.add();manager_lock=threading.Condition()
        manager_held,callback_entered=threading.Event(),threading.Event()
        def cb(sid):
            callback_entered.set()
            with manager_lock: pass
        self.app(cb)
        def opener():
            with manager_lock:
                manager_held.set()
                if not callback_entered.wait(1): raise AssertionError('no callback')
                s.inc_activities_value('shellSession')
        opening,oe=launch(opener,'opening');self.assertTrue(manager_held.wait(1))
        closing,ce=launch(lambda:self.a.close_session(s),'closing')
        join(opening,.8);join(closing,.8)
        self.assertFalse(oe+ce)
    def test_close_all_callbacks_and_session_close_release_global_lock(self):
        sessions=[self.add(str(n)) for n in range(3)]
        seen=[]
        def check():
            got=self.a._sessions_semaphore.acquire(timeout=.1)
            if got:self.a._sessions_semaphore.release()
            seen.append(got)
        def cb(sid):
            t,err=launch(check);join(t);self.assertFalse(err)
        self.app(cb)
        self.a._close_all_sessions()
        self.assertEqual(seen,[True]*3);self.assertFalse(self.a._sessions)
        self.assertFalse(self.a._sessions_closing)
    def test_duplicate_close_has_one_callback(self):
        s=self.add();entered,release=threading.Event(),threading.Event();calls=[]
        self.app(lambda sid:(calls.append(sid),entered.set(),release.wait(2)))
        first,errors=launch(lambda:self.a.close_session(s));self.assertTrue(entered.wait(1))
        threads=[launch(lambda:self.a.close_session(s)) for _ in range(12)]
        for t,e in threads:join(t);self.assertFalse(e)
        release.set();join(first);self.assertFalse(errors);self.assertEqual(calls,['one'])
    def test_stale_session_cannot_close_replacement(self):
        old=self.Session(self.a,sid='one');fresh=self.add();calls=[]
        self.app(lambda sid:calls.append(sid))
        self.a.close_session(old)
        self.assertIs(self.a._sessions['one'],fresh);self.assertEqual(calls,[])
    def test_callback_can_open_new_session_without_unloading_it(self):
        old=self.add();destroyed=[]
        self.app(lambda sid:self.a.open_session(OPEN),lambda force:(destroyed.append(force),True)[1])
        self.a.close_session(old)
        self.assertEqual(len(self.a._sessions),1);self.assertFalse(destroyed)
        self.assertIn('test',self.a._apps)
    def test_idle_unload_serializes_new_publication(self):
        old=self.add();entered,release=threading.Event(),threading.Event()
        self.app(destroy=lambda force:(entered.set(),release.wait(2),True)[2])
        closing,ce=launch(lambda:self.a.close_session(old));self.assertTrue(entered.wait(1))
        opening,oe=launch(lambda:self.a.open_session(OPEN))
        time.sleep(.05)
        with self.a._sessions_semaphore:self.assertFalse(self.a._sessions)
        self.assertTrue(opening.is_alive(),'new session published during old app unload')
        # Heartbeat still works while destroy waits under the app registry lock.
        status,se=launch(self.a.get_active_sessions_status);join(status,.2);self.assertFalse(se)
        release.set();join(closing);join(opening);self.assertFalse(ce+oe)
        self.assertEqual(len(self.a._sessions),1)
    def test_all_close_does_not_unload_newly_opened_session(self):
        self.add('old1');self.add('old2');calls=[];destroyed=[]
        def callback(sid):
            calls.append(sid)
            if sid=='old1': self.a.open_session(OPEN)
        self.app(callback,lambda force:(destroyed.append(force),True)[1])
        self.a._close_all_sessions()
        self.assertEqual(calls,['old1','old2']);self.assertEqual(len(self.a._sessions),1)
        self.assertFalse(destroyed)
    def test_update_wait_does_not_hold_app_registry_lock(self):
        self.a._sessions_update_status='INPROGRESS'
        opening,oe=launch(lambda:self.a.open_session(OPEN),'open-during-update')
        time.sleep(.05)
        def update():
            self.a._unload_apps()
            with self.a._sessions_semaphore:
                self.a._sessions_update_status=''
                self.a._sessions_semaphore.notify_all()
        updater,ue=launch(update,'finish-update')
        join(updater,.5);join(opening,.5)
        self.assertFalse(ue+oe);self.assertEqual(len(self.a._sessions),1)
    def test_expired_update_wait_rejects_without_publication(self):
        self.a._sessions_update_status='INPROGRESS'
        with self.assertRaisesRegex(Exception,'Update in progress'):
            self.a.open_session(dict(OPEN,connectionTimeout=2))
        self.assertFalse(self.a._sessions)
    def test_optional_connection_timeout_can_be_missing_or_invalid(self):
        msg=dict(OPEN);msg.pop('connectionTimeout')
        self.a.open_session(msg)
        self.a.open_session(dict(OPEN,connectionTimeout='invalid'))
        self.assertEqual(len(self.a._sessions),2)
    def test_callback_exception_does_not_skip_other_apps_or_cleanup(self):
        s=self.add();seen=[]
        def bad(sid): raise RuntimeError('injected callback error')
        self.app(bad)
        self.a._apps['other']=SimpleNamespace(on_conn_close=lambda sid:seen.append(sid),destroy=lambda force:True)
        self.a.close_session(s)
        self.assertEqual(seen,['one']);self.assertFalse(self.a._sessions)
        self.assertFalse(self.a._sessions_closing);self.assertTrue(self.a.errors)
    def test_app_registry_snapshot_survives_callback_mutation(self):
        s=self.add();seen=[]
        def change(sid):
            with self.a._libs_apps_semaphore:self.a._apps.pop('other',None)
        self.app(change)
        self.a._apps['other']=SimpleNamespace(on_conn_close=lambda sid:seen.append(sid),destroy=lambda force:True)
        self.a.close_session(s);self.assertEqual(seen,['one'])
    def test_stress_450_concurrent_opens_closes_and_heartbeat(self):
        errors=[];stop=threading.Event();beats=[];calls=[];guard=threading.Lock()
        # No app unload in this stress: a permanent anchor session models a
        # concurrent active user. Idle/unload races are exercised separately.
        self.add('anchor')
        def cb(sid):
            with guard:calls.append(sid)
        self.app(cb)
        def worker():
            for _ in range(75):
                result=self.a.open_session(OPEN)
                with self.a._sessions_semaphore:s=self.a._sessions.get(result['idSession'])
                if s is not None:self.a.close_session(s)
        def heartbeat():
            while not stop.is_set():
                self.a.get_active_sessions_status();beats.append(1);stop.wait(.002)
        h,he=launch(heartbeat,'heartbeat-stress')
        workers=[launch(worker,'lifecycle-%s'%i) for i in range(6)]
        for t,e in workers:join(t,8);errors.extend(e)
        stop.set();join(h);self.assertFalse(errors+he);self.assertTrue(beats)
        self.assertEqual(len(calls),450);self.assertEqual(len(set(calls)),450)
        self.assertEqual(set(self.a._sessions),{'anchor'});self.assertFalse(self.a._sessions_closing)
    def test_stress_close_all_racing_with_new_sessions(self):
        calls=[];lock=threading.Lock();stop=threading.Event()
        self.app(lambda sid:(lock.acquire(),calls.append(sid),lock.release()))
        # Registry-only stress; app reload/unload interlocks have dedicated tests.
        self.a._unload_apps=lambda:None
        def worker():
            for _ in range(100):
                response=self.a.open_session(OPEN)
                with self.a._sessions_semaphore:s=self.a._sessions.get(response['idSession'])
                if s is not None:self.a.close_session(s)
        def close_all():
            for _ in range(75):self.a._close_all_sessions();time.sleep(.001)
        tasks=[launch(worker) for _ in range(2)]+[launch(close_all)]
        for t,e in tasks:join(t,5);self.assertFalse(e)
        self.a._close_all_sessions()
        self.assertFalse(self.a._sessions);self.assertFalse(self.a._sessions_closing)
        self.assertEqual(len(calls),200);self.assertEqual(len(set(calls)),200)


class OSProxy:
    def __init__(self):
        self.ready=threading.Event();self.release_blocking=threading.Event()
        self.reaped=set();self.calls=[];self.signals=[];self.mutex=threading.Lock()
    def __getattr__(self,k):return getattr(os,k)
    def kill(self,pid,sig):self.signals.append((pid,sig))
    def waitpid(self,pid,options):
        with self.mutex:self.calls.append((pid,options))
        if options==0:self.release_blocking.wait(5)
        with self.mutex:
            if pid in self.reaped:raise ChildProcessError(errno.ECHILD,'already collected')
            if self.ready.is_set() or options==0:
                self.reaped.add(pid);return pid,0
        return 0,0


class ProcessTests(unittest.TestCase):
    def terminal(self,api=None):
        self.api=api or OSProxy();env,A,S=load(self.api);a=A();s=S(a)
        app=env['Shell'](a)
        manager=SimpleNamespace(_cinfo=s,_shlmain=app)
        terminal=env['LinuxMac'](manager,1,80,24)
        return terminal,env,a,s,app
    def test_bounded_wait_and_eventual_reap(self):
        t,env,a,s,app=self.terminal();t._ppid=424242
        t._activity_registered=True;s._activities['shellSession']=1
        started=time.monotonic();thread,errors=launch(t.terminate)
        try:
            join(thread,1.6)
            self.assertLess(time.monotonic()-started,1.6)
            self.assertFalse(errors)
            self.assertTrue(all(options==os.WNOHANG for pid,options in self.api.calls))
            self.assertEqual(self.api.signals,[(424242,signal.SIGTERM),(424242,signal.SIGKILL)])
            self.assertIn(424242,app._process_reaper._pending)
            self.assertEqual(s._activities['shellSession'],0)
        finally:
            self.api.ready.set();self.api.release_blocking.set();join(thread)
        deadline=time.monotonic()+2
        while getattr(app,'_process_reaper',None) and app._process_reaper._thread is not None and time.monotonic()<deadline:time.sleep(.02)
        self.assertIn(424242,self.api.reaped)
        self.assertIsNone(app._process_reaper._thread)
        self.assertFalse(app._process_reaper._pending)
    def test_pty_fd_closed_and_activity_decremented_once(self):
        t,env,a,s,app=self.terminal();fd=os.open('/dev/null',os.O_RDWR)
        t._pio=fd;t._reader=io.open(fd,'rb',closefd=False);t._writer=io.open(fd,'wb',closefd=False)
        t._activity_registered=True;s._activities['shellSession']=1
        try:
            t.terminate();t.terminate()
            self.assertEqual(s._activities['shellSession'],0)
            with self.assertRaises(OSError):os.fstat(fd)
        finally:
            try:os.close(fd)
            except OSError:pass
    def test_no_decrement_before_activity_registered(self):
        t,env,a,s,app=self.terminal();t.terminate();t.terminate()
        self.assertEqual(s._activities['shellSession'],0)
    def test_pty_master_closed_after_one_termination(self):
        t,env,a,s,app=self.terminal();fd=os.open('/dev/null',os.O_RDWR)
        t._pio=fd;t._reader=io.open(fd,'rb',closefd=False)
        try:
            t.terminate()
            with self.assertRaises(OSError):os.fstat(fd)
        finally:
            try:os.close(fd)
            except OSError:pass
    def test_unreapable_shell_keeps_heartbeat_and_new_sessions_responsive(self):
        terminal,env,a,s,app=self.terminal();a._sessions['one']=s;a._apps['shell']=app
        terminal._ppid=424242;terminal._activity_registered=True;s._activities['shellSession']=1
        mgr=terminal._manager
        mgr._semaphore=threading.Condition();mgr._bclose=False;mgr._idses='one'
        mgr._shell_list={1:terminal};mgr._timeout_counter=Counter()
        mgr.get_idses=lambda:'one'
        mgr.terminate=lambda:env['ShellManager'].terminate(mgr)
        app._list['test-manager']=mgr
        entered=threading.Event();previous_kill=self.api.kill
        def kill(pid,sig):entered.set();previous_kill(pid,sig)
        self.api.kill=kill
        data=json.dumps(dict(type=1,id=1))
        closing,ce=launch(lambda:env['ShellManager']._on_data(mgr,None,ord('s'),data),'close-unreapable-shell')
        try:
            self.assertTrue(entered.wait(.5))
            session_close,se=launch(lambda:a.close_session(s),'close-owning-session')
            status,he=launch(a.get_active_sessions_status,'heartbeat-during-stalled-reap')
            opening,oe=launch(lambda:a.open_session(OPEN),'new-session-during-stalled-reap')
            join(status,.25);join(opening,.25)
            self.assertFalse(he+oe)
            join(closing,1.5);join(session_close,.5);self.assertFalse(ce+se)
            self.assertIn(424242,app._process_reaper._pending)
            self.assertEqual(len(a._sessions),1)
        finally:
            self.api.ready.set();self.api.release_blocking.set();join(closing)
        reaper=app._process_reaper._thread
        if reaper is not None:join(reaper,2)
        self.assertFalse(app._process_reaper._pending)
    def test_already_reaped_pid_is_never_signalled(self):
        api=OSProxy();api.reaped.add(424242)
        t,env,a,s,app=self.terminal(api);t._ppid=424242;t.terminate()
        self.assertFalse(api.signals);self.assertFalse(app._process_reaper._pending)
    def test_concurrent_termination_is_idempotent(self):
        api=OSProxy();api.ready.set()
        t,env,a,s,app=self.terminal(api);t._ppid=424242
        t._activity_registered=True;s._activities['shellSession']=1
        workers=[launch(t.terminate) for _ in range(20)]
        for worker,err in workers:join(worker);self.assertFalse(err)
        self.assertEqual(s._activities['shellSession'],0)
        self.assertEqual(len(api.calls),1)
    def test_one_reaper_shared_across_reload_and_no_idle_worker(self):
        t,env,a,s,app=self.terminal()
        self.assertIsNone(app._process_reaper._thread)
        again=env['Shell'](a);self.assertIs(app._process_reaper,again._process_reaper)
        for pid in range(500000,500100):app._process_reaper.add(pid)
        worker=app._process_reaper._thread
        self.assertTrue(worker.is_alive())
        self.assertEqual(len(app._process_reaper._pending),100)
        self.api.ready.set();join(worker,2)
        self.assertFalse(app._process_reaper._pending)
        self.assertIsNone(app._process_reaper._thread)
        again._process_reaper.add(600000)
        late=again._process_reaper._thread
        if late is not None:join(late,2)
        self.assertFalse(again._process_reaper._pending)
    def test_initialization_failure_closes_owned_fd(self):
        t,env,a,s,app=self.terminal();fd=os.open('/dev/null',os.O_RDWR)
        self.api.reaped.add(424242)
        env['pty']=SimpleNamespace(fork=lambda:(424242,fd))
        def fail(*args):raise OSError(errno.EIO,'injected fcntl failure')
        env['fcntl']=SimpleNamespace(fcntl=fail,F_GETFL=fcntl.F_GETFL)
        try:
            t.open_session(None,None)
            with self.assertRaises(OSError):os.fstat(fd)
            self.assertEqual(s._activities['shellSession'],0)
        finally:
            try:os.close(fd)
            except OSError:pass
    def test_poll_interrupted_and_child_not_owned(self):
        t,env,a,s,app=self.terminal()
        def interrupted(pid,options):raise InterruptedError(errno.EINTR,'injected')
        self.api.waitpid=interrupted;t._ppid=424242
        self.assertTrue(t._processIsAlive())
        def not_owned(pid,options):raise ChildProcessError(errno.ECHILD,'injected')
        self.api.waitpid=not_owned
        self.assertFalse(t._processIsAlive());t.terminate()
        self.assertFalse(self.api.signals)
    def test_foreground_group_in_different_session_is_never_signalled(self):
        api=OSProxy();api.tcgetpgrp=lambda fd:333;api.getpgrp=lambda:222;api.getsid=lambda group:999
        calls=[];api.killpg=lambda group,sig:calls.append((group,sig))
        env,A,S=load(api);env['_stop_shell_foreground'](111,5)
        self.assertEqual(calls,[])
    def test_own_process_group_is_never_signalled(self):
        api=OSProxy();api.tcgetpgrp=lambda fd:222;api.getpgrp=lambda:222;api.getsid=lambda group:111
        calls=[];api.killpg=lambda group,sig:calls.append((group,sig))
        env,A,S=load(api);env['_stop_shell_foreground'](111,5)
        self.assertEqual(calls,[])
    def test_foreground_switch_prevents_signalling_stale_group(self):
        api=OSProxy();current=[333];api.tcgetpgrp=lambda fd:current[0]
        api.getpgrp=lambda:222;api.getsid=lambda group:111;calls=[]
        def signal_group(group,sig):calls.append((group,sig));current[0]=444
        api.killpg=signal_group
        env,A,S=load(api);env['_stop_shell_foreground'](111,5)
        self.assertEqual(calls,[(333,signal.SIGTERM)])


def process_rows():
    rows={}
    for line in subprocess.check_output(['/bin/ps','-axo','pid=,ppid=,stat=,lstart=,comm='],text=True).splitlines():
        p=line.split(None,8)
        if len(p)==9:rows[int(p[0])]=dict(parent=int(p[1]),state=p[2],birth=' '.join(p[3:8]),exe=p[8])
    return rows


@unittest.skipUnless(sys.platform == 'darwin', 'real PTY process checks use macOS ps output')
class PTYTests(unittest.TestCase):
    def setUp(self):
        self.env,A,S=load();self.a=A();self.s=S(self.a);self.a._sessions['one']=self.s
        self.home=tempfile.TemporaryDirectory(prefix='dwagent-patch-qa-',dir='/private/tmp')
        account=SimpleNamespace(pw_uid=os.getuid(),pw_dir=self.home.name,pw_shell='/bin/sh')
        self.pwd=mock.patch.object(pwd,'getpwuid',lambda uid:account);self.pwd.start()
        self.app=self.env['Shell'](self.a);self.a._apps['shell']=self.app
        self.managers=[];self.known={}
    def tearDown(self):
        # Only emergency fallback: tests assert disappearance before this.
        for m in self.managers:
            try:m.terminate()
            except Exception:pass
        rows=process_rows()
        for pid,birth in self.known.items():
            if pid in rows and rows[pid]['birth']==birth:
                try:os.kill(pid,signal.SIGKILL)
                except ProcessLookupError:pass
        for m in self.managers:m.join(2)
        self.pwd.stop();self.home.cleanup()
    def open(self):
        class Socket:
            def __init__(self):self.frames=[];self.closed=False
            def get_properties(self):return {}
            def accept(self,n,events):self.events=events
            def send_string(self,s):self.frames.append(json.loads(s))
            def close(self):self.closed=True
        ws=Socket();mgr=self.app._add_shell_manager(self.s,ws);self.managers.append(mgr)
        mgr._on_data(ws,ord('s'),json.dumps(dict(type=0,id=1,cols=80,rows=24)))
        mgr._on_data(ws,ord('s'),json.dumps(dict(type='init')))
        sh=mgr._shell_list[1];pid=sh._ppid
        rows=process_rows()
        if pid in rows:self.known[pid]=rows[pid]['birth']
        return mgr,ws,sh,pid
    def wait_gone(self,pids,limit=3):
        deadline=time.monotonic()+limit
        while time.monotonic()<deadline:
            rows=process_rows()
            remain=[p for p in pids if p in rows and rows[p]['birth']==self.known[p]]
            if not remain:return
            time.sleep(.025)
        self.fail('real processes remain before fallback: %s'%json.dumps({p:rows[p] for p in remain}))
    def close(self,mgr,ws):
        mgr._on_data(ws,ord('s'),json.dumps(dict(type=1,id=1)))
        mgr._on_data(ws,ord('s'),json.dumps(dict(type='term')))
        join(mgr,2)
    def test_real_shell_and_foreground_child_are_gone(self):
        mgr,ws,sh,pid=self.open()
        mgr._on_data(ws,ord('s'),json.dumps(dict(type=2,id=1,data='sleep 120\r')))
        deadline=time.monotonic()+2;children=[]
        while time.monotonic()<deadline:
            rows=process_rows();children=[p for p,r in rows.items() if r['parent']==pid and r['exe']=='sleep']
            if children:break
            time.sleep(.025)
        self.assertTrue(children,'no actual foreground child observed')
        for child in children:self.known[child]=rows[child]['birth']
        self.close(mgr,ws);self.wait_gone([pid]+children)
        self.assertFalse(self.app._list);self.assertTrue(ws.closed)
        self.assertEqual(self.s._activities['shellSession'],0)
    def test_foreground_cleanup_with_inherited_ignored_term(self):
        previous=signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
        try:self.test_real_shell_and_foreground_child_are_gone()
        finally:signal.signal(signal.SIGTERM,previous)
    def test_foreground_job_ignoring_hup_and_term_is_killed(self):
        mgr,ws,sh,pid=self.open()
        command="/usr/bin/python3 -c 'import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGHUP,signal.SIG_IGN);print(\"FG_READY\",flush=True);time.sleep(120)'\r"
        mgr._on_data(ws,ord('s'),json.dumps(dict(type=2,id=1,data=command)))
        deadline=time.monotonic()+5;children=[];ready=False
        while time.monotonic()<deadline:
            rows=process_rows()
            children=[p for p,r in rows.items() if r['parent']==pid and ('python' in r['exe'].lower())]
            ready=any('FG_READY\r\n' in f.get('data','') for f in ws.frames)
            if children and ready:break
            time.sleep(.025)
        self.assertTrue(children,'real foreground Python child not observed: '+json.dumps(ws.frames)[-1200:])
        self.assertTrue(ready,'foreground signal handlers were not confirmed ready')
        for child in children:self.known[child]=rows[child]['birth']
        self.close(mgr,ws);self.wait_gone([pid]+children)
        self.assertEqual(self.s._activities['shellSession'],0)
    def test_repeated_immediate_open_close_no_process_or_fd_growth(self):
        baseline=len(os.listdir('/dev/fd'))
        pids=[];times=[]
        for _ in range(30):
            mgr,ws,sh,pid=self.open();pids.append(pid)
            started=time.monotonic();self.close(mgr,ws);times.append(time.monotonic()-started)
        self.wait_gone(pids,4)
        self.assertEqual(self.s._activities['shellSession'],0)
        self.assertFalse(self.app._list)
        self.assertLessEqual(len(os.listdir('/dev/fd')),baseline+1)
        self.assertLess(max(times),1.7)
        print('METRIC immediate_close_cycles=30 max_close_seconds=%.6f fd_before=%d fd_after=%d uid=%d'%
              (max(times),baseline,len(os.listdir('/dev/fd')),os.getuid()),flush=True)
    def test_real_term_resistant_child_gets_kill_and_is_reaped(self):
        # A controlled direct child ignores HUP/TERM. No PTY or other processes.
        script='import os,signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGHUP,signal.SIG_IGN);print(os.getpid(),flush=True);time.sleep(120)'
        child=subprocess.Popen([sys.executable,'-B','-c',script],stdout=subprocess.PIPE,text=True)
        pid=int(child.stdout.readline());child.stdout.close()
        self.known[pid]=process_rows()[pid]['birth']
        mgr=SimpleNamespace(_cinfo=self.s,_shlmain=self.app)
        sh=self.env['LinuxMac'](mgr,1,80,24);sh._ppid=pid
        sh._activity_registered=True;self.s._activities['shellSession']=1
        started=time.monotonic();sh.terminate()
        self.wait_gone([pid]);self.assertLess(time.monotonic()-started,1.6)
        with self.assertRaises(ChildProcessError):os.waitpid(pid,os.WNOHANG)
        child.returncode=-signal.SIGKILL
        self.assertEqual(self.s._activities['shellSession'],0)


if __name__=='__main__':
    unittest.main(verbosity=2)
