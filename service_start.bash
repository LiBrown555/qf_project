#!/bin/bash
ROOT=/home/cfqf/qf_project
PYTHON=/usr/bin/python3
export PYTHONPATH=$ROOT/src/iot_task_exec:$ROOT/src:$PYTHONPATH

cd $ROOT && $PYTHON main.py &
cd $ROOT && $PYTHON src/iot_task_exec/task_exec.py &
cd $ROOT && $PYTHON src/iot_task_exec/task_plan.py &

wait
