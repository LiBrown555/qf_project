import time
from multiprocessing import Process

from task_plan import TaskPlan
from task_exec import TaskExec


def run_task_plan():
    task_plan = TaskPlan()
    task_plan.main()      


def run_task_exec():
    task_exec = TaskExec()
    task_exec.main()      


if __name__ == "__main__":
    p_plan = Process(target=run_task_plan, name="task_plan_proc")
    p_exec = Process(target=run_task_exec, name="task_exec_proc")

    p_plan.start()
    p_exec.start()

    try:
        while True:
            if not p_plan.is_alive() and not p_exec.is_alive():
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("收到 Ctrl+C，准备停止子进程...")
        if p_plan.is_alive():
            p_plan.terminate()
        if p_exec.is_alive():
            p_exec.terminate()
    finally:
        p_plan.join()
        p_exec.join()
        print("所有子进程已退出，主程序结束。")