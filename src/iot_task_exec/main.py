import time
import signal
from multiprocessing import Process

from task_plan import TaskPlan
from task_exec import TaskExec


def run_task_plan():
    task_plan = TaskPlan()
    task_plan.main()      # 使用你原来的逻辑，里面自己有 signal 和 while 循环


def run_task_exec():
    task_exec = TaskExec()
    task_exec.main()      # 同样保持原逻辑不动


if __name__ == "__main__":
    p_plan = Process(target=run_task_plan, name="task_plan_proc")
    p_exec = Process(target=run_task_exec, name="task_exec_proc")

    p_plan.start()
    p_exec.start()

    try:
        # 主进程只负责“看着”两个子进程
        while True:
            if not p_plan.is_alive() and not p_exec.is_alive():
                break
            time.sleep(1)
    except KeyboardInterrupt:
        # Ctrl+C 时优雅退出：先让子进程走自己的 signal 处理逻辑
        print("收到 Ctrl+C，准备停止子进程...")
        if p_plan.is_alive():
            p_plan.terminate()
        if p_exec.is_alive():
            p_exec.terminate()
    finally:
        p_plan.join()
        p_exec.join()
        print("所有子进程已退出，主程序结束。")