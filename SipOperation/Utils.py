# -*- coding: utf-8 -*-
__author__ = 'jiazhu'

"""
@author:jiazhu
@time: 17/2/15 10:40
"""
import time
import subprocess
import os
import sys
import logging
import logging.handlers


def all_file_path(root_directory, extension_name):
    """

    :return: 遍历文件目录
    """

    file_dic = {}
    for parent, dirnames, filenames in os.walk(root_directory):
        for filename in filenames:
            if 'filter' not in filename:
                if filename.endswith(extension_name):
                    path = os.path.join(parent, filename).replace('\\', '/')
                    file_dic[filename] = path
    return file_dic


def case_yaml_file(yaml_path):
    """
    :return: 返回yaml_path 下的 yaml场景文件列表列表
    """
    return all_file_path(yaml_path, '.yaml')


def get_now_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))


def sleep(s):
    return time.sleep(s)


def cmd(cmd):
    return subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


LOGGERS = set()

def create_http_result_logger(logname,logfilenam):
    """Creat a logger named specified name with the level set in config file.
    """
    loggo = logging.getLogger(logname)
    if loggo in LOGGERS:
        return loggo

    loggo.setLevel(logging.DEBUG)

    lform = '%(asctime)s.%(msecs)03d:%(message)s'
    tform = '%y%m%d %H:%M:%S'
    lformatter = logging.Formatter(lform,tform)

    filestrmhand = logging.handlers.RotatingFileHandler(logfilenam,maxBytes=1024*1024*100, backupCount=100)

    filestrmhand.setLevel(logging.DEBUG)
    filestrmhand.setFormatter(lformatter)
    loggo.addHandler(filestrmhand )
    LOGGERS.add(loggo)
    return loggo

def create_debug_logger(logname,logfilenam):
    """Creat a logger named specified name with the level set in config file.
    """
    loggo = logging.getLogger(logname)
    if loggo in LOGGERS:
        return loggo

    loggo.setLevel(logging.DEBUG)

    lform = '%(asctime)s.%(msecs)03d: [%(levelname)s] [%(name)s] [%(funcName)s] %(message)s'
    tform = '%y%m%d %H:%M:%S'
    lformatter = logging.Formatter(lform,tform)

    strmhand = logging.StreamHandler()
    strmhand.setLevel(logging.DEBUG)
    strmhand.setFormatter(lformatter)
    loggo.addHandler(strmhand)

    filestrmhand = logging.handlers.RotatingFileHandler(logfilenam, maxBytes=1024 * 1024 * 100, backupCount=100)
    filestrmhand.setLevel(logging.DEBUG)
    filestrmhand.setFormatter(lformatter)
    loggo.addHandler(filestrmhand )

    LOGGERS.add(loggo)

    return loggo


def create_folder(foldername):
    """Creat a folder named foldername in root path"""

    folder_path = os.path.join(sys.path[0], foldername)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

def getattr_with_lock(object,name,lock):
    lock.acquire()
    value = getattr(object,name)
    lock.release()
    return value

def setattr_with_lock(object,name,value,lock):
    lock.acquire()
    setattr(object,name,value)
    lock.release()



def pop_random_online_user():
    """
    在userpool 的online 用户列表中随机选择一个用户返回，并在原列表中删除该用户
    :return:
    """
    pass

def pop_random_offline_user():
    """
    在userpool 的offline 用户列表中随机选择一个用户返回，并在原列表中删除该用户
    :return:
    """

def pop_random_groupid():
    """

    :return:
    """

def pop_():
    pass

if __name__ == '__main__':
    pass
