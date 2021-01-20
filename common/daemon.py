

import os,sys,time

def daemon_init(stdin='/dev/null',stdout='/dev/null',stderr='/dev/null'):
    sys.stdin = open(stdin,'r')
    sys.stdout = open(stdout,'a+')
    sys.stderr = open(stderr,'a+')
    try:
        pid = os.fork()
        if pid > 0:        #parrent
            os._exit(0)
    except OSError,e:
        sys.stderr.write("first fork failed!!"+e.strerror)
        os._exit(1)
 
    os.setsid()
    os.chdir("/")
    os.umask(0)
 
    try:
        pid = os.fork()     #第二次进行fork,为了防止会话首进程意外获得控制终端
        if pid > 0:
            os._exit(0)     #父进程退出
    except OSError,e:
        sys.stderr.write("second fork failed!!"+e.strerror)
        os._exit(1)
 
    # 孙进程
    sys.stdout.write("Daemon has been created! with pid: %d\n" % os.getpid())

