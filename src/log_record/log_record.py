#!/usr/bin/env python3
#coding=utf-8

import os
import logging
from logging.handlers import TimedRotatingFileHandler

class LogAndRecord:
    def __init__(self):
        super(LogAndRecord, self).__init__()
       

    def log_init(self, log_path, name):
        """ 初始化日志 """
        try:
            directory_path = os.path.dirname(log_path)
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)
            self.logger = logging.getLogger(name)
            self.logger.propagate = False
            if not self.logger.handlers:
                self.logger.setLevel(logging.DEBUG)
                file_handler = TimedRotatingFileHandler(log_path, when='midnight', interval=1, backupCount=30, encoding='utf-8')
                file_handler.setLevel(logging.INFO)
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging.DEBUG)
                formatter = logging.Formatter('%(asctime)s [%(levelname)s] <%(lineno)d> %(filename)s.%(funcName)s():%(message)s')
                file_handler.setFormatter(formatter)
                console_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
                self.logger.addHandler(console_handler)
            return True
        
        except Exception as e:
            print(f"log_record:日志初始化错误{str(e)}")
            return False
        
