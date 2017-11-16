# -*- coding: utf-8 -*-
"""
@author:jiazhu
@time: 17/02/10 18:44
"""
import multiprocessing
from SipOperation.SipCall import *
from public.UserPoolCache import UserPoolCache
import public.Utils as Utils
from public.UserInfo import User
from public.Scene import Scene
import sys

normal_finished = False


def generate_phone_num(i_num):
    if sys.argv[1] == "Test":
        return str(520100000001 + i_num)
    else:
        print ("No such environment. %s" % sys.argv[1])
        sys.exit(1)


def worker(p_stop_signal, result_queue):
    nowtime_str = time.strftime('%Y%m%d_%H%M%S', time.localtime(time.time()))
    print nowtime_str
    #LINUX
    DebugLogPath = Utils.create_folder("TestResult/DebugLog/")
    ResultLogPath = Utils.create_folder("TestResult/HttpResult/")
    CountLogPath = Utils.create_folder("TestResult/CountResult/")
    LockLogPath = Utils.create_folder("TestResult/LockResult/")

    #WINDOWS
    """DebugLogPath = Utils.create_folder("TestResult\\DebugLog\\")
    ResultLogPath = Utils.create_folder("TestResult\\HttpResult\\")"""
    debug_log_file = DebugLogPath + nowtime_str + "_Debug.log"
    result_log_file = ResultLogPath + nowtime_str + "_Http_detail.log"
    count_log_file = CountLogPath + nowtime_str + "_http_result.log"
    lock_log_file = LockLogPath + nowtime_str + "_lock.log"

    logger = Utils.create_debug_logger("MXTest", debug_log_file)
    logger_db = Utils.create_http_result_logger("Result", result_log_file)
    logger_cn = Utils.create_http_result_logger("Count", count_log_file)
    logger_lc = Utils.create_http_result_logger("Lock", lock_log_file )

    user_set = []
    # 这里可以考虑使用excel表格导入数据的方式实现批量导入
    for j in range(int(sys.argv[3])):
        user_info_dict = {
            "userPhoneNum": generate_phone_num(j),
            "userPassword": generate_phone_num(j),
            "runEnvir": "test",
            "deviceType": "tv",
            "appVersion": "2.4.1",
            "basicToken": None,
            "TGT_id": None,
            "inConf": False,
            "inConfID": None,
            "isChairman": False,
            "isGroupOwner": False,
            "inGroupID": None}
        ws_client = None
        user = User(user_info_dict, ws_client)
        user_set.append(user)

    user_pool = UserPoolCache(user_set, p_stop_signal, "offline_idle")
    u = Scene(sys.argv[2], user_pool, p_stop_signal)
    u.run()

    print "Test Fine."
    result_queue.put("Success")
    p_stop_signal.set()


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print """Please run as follow:
        python run.py CC02(environment) XXX(your yamlfile) XXX(how many locust your need.)
        e.g.: python run.py Test "./testyaml/login.yaml" 1
        """
        sys.exit()
    w1 = None
    try:
        result_queue = multiprocessing.Queue()
        for i in range(1):
            p_stop_signal = multiprocessing.Event()
            w1 = multiprocessing.Process(name="test",
                                         target=worker,
                                         args=(p_stop_signal, result_queue))
            w1.start()
            while not p_stop_signal.is_set():
                time.sleep(1)
            w1.terminate()
            if result_queue.empty():
                print "Response to interrupt the test signal, in the ENDSIPP .."
                sip_end_call = SipCallMap.get_instance().get_sip_call("ENDSIPP")
                sip_end_call.end_all_sipp()
                CommanderMap.get_instance().release_commander("ENDSIPP")
                print ("end all sipp")

    except KeyboardInterrupt:
        if w1:
            w1.terminate()
        print "Use the key to end the program, in the ENDSIPP .."
        sip_end_call = SipCallMap.get_instance().get_sip_call("ENDSIPP")
        sip_end_call.end_all_sipp()
        CommanderMap.get_instance().release_commander("ENDSIPP")
        print ("end all sipp")
