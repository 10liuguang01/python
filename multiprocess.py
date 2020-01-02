# 
# 多进程管理，实现的功能有：
# 1. 子进程退出时，回收僵尸进程，重新创建进程
# 2. 父进程退出时，友好关闭子进程，然后再退出

import errno
from multiprocessing import Process, current_process
import logging
import os
import signal
import time

# {pid => { setting => {}, process => Process}}
p_map={}
    
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)-15s - %(levelname)s - %(message)s'
)

# 子进程函数
def run(**args):
    logging.info('runnint arg is :%s', args)
    time.sleep(args["sleep"])
    exitcode = 3
    logging.info('exit child process %s with exitcode %s', current_process().pid, exitcode)
                 
    os._exit(exitcode)

# 退出信号的处理函数
def wait_child(signum, frame):
    logging.info('receive SIGCHLD')
    try:
        while True:
            # os.waitpid 获取退出的子进程，并回收子进程
            cpid, status = os.waitpid(-1, os.WNOHANG)
            if cpid == 0:
                logging.info('no child process was immediately available')
                break
            exitcode = status >> 8
            logging.info('child process %s exit with exitcode %s', cpid, exitcode)
            
            # 重建子进程
            exit_p=p_map[cpid]
            exit_p["process"].join()
            del p_map[cpid]
            p = Process(target=run, kwargs=exit_p["setting"])
            p.start()
            # 更新map
            
            p_map[p.pid]={"setting": exit_p["setting"], "process": p}
            logging.info('p.pid is :%s, p_map is : %s', p.pid, p_map)
    except OSError as e:
        if e.errno == errno.ECHILD:
            logging.warning('current process has no existing unwaited-for child processes.')
            os._exit(exitcode)
        else:
            raise
    logging.info('handle SIGCHLD end')

    
def main():
    # 监听退出信号，退出所有子进程
    def terminate_handler(signum, frame):
        logging.info('Signal %s received. Stopping gracefully...' % signum)
        for (pid, p) in p_map.items():
            try:
                p["process"].terminate()
            except Exception as e:
                logging.warning('terminate error: %s', e)
        os._exit(0)
    signal.signal(signal.SIGTERM, terminate_handler)
    signal.signal(signal.SIGINT, terminate_handler)

    # 监听子进程的退出信号，重建子进程
    signal.signal(signal.SIGCHLD, wait_child)

    # 子进程 1 
    parse_setting1={"xxx": 1111111, "sleep": 6}
    p = Process(target=run, kwargs=parse_setting1)
    p.start()
    p_map[p.pid]={"setting": parse_setting1, "process": p}

    # 子进程 2 
    parse_setting2={"xxx": 222222, "sleep": 10}
    p2 = Process(target=run, kwargs=parse_setting2)
    p2.start()
    p_map[p2.pid]={"setting": parse_setting2, "process": p2}

    while True:
        time.sleep(10)

if __name__ == "__main__":
    main()
