# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
import logging
import json
import copy
import time
import random
import traceback
import requests
from collections import deque
from public.ConstantSet import Constant
from public.HttpClient import HttpClient
from requests.exceptions import ConnectionError


class EnablePPTShareAction(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.attach_conf_id = None
        self.conf_obj = None
        self.executor_phone_num = None
        self.properly_executed = False
        self.check_result = False
        self._logger = logging.getLogger(log_name)
        self._logger_cn = logging.getLogger("Count")
        self.Tager = False

    def _execute_action(self):
        try:
            if "check_result" in self.case_info_dict:
                self.check_result = self.case_info_dict["check_result"]

            if "check_Tager" in self.case_info_dict:
                self.Tager = self.case_info_dict["check_Tager"]

            """
            if self.check_result:
                self.user_pool.cache_lock.acquire()
                self.executor_phone_num = self.user_pool.in_conf_mem_phone_num_list.pop()
                self.user_pool.cache_lock.release()
            else:
                # 在in_conf_mem_phone_num_list中随机选取一个元素"""
            self.executor_phone_num = random.choice(self.user_pool.in_conf_mem_phone_num_list)

            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]
            self.attach_conf_id = self.executor_obj.attach_conf_id

            http_response = self._execute_http_request()

            # 同一个会议中，不同要分享ppt的时间间隔要超过10秒。否则返回400
            if (http_response.status_code == 200) or (http_response.status_code == 400):
                self._logger.info("Enable PPT Share Success!")
                self.properly_executed = True
                return True
            else:
                self._logger.error("Enable PPT Share Http Fail!")
                return False
        except:
            self._logger.error("Return False because of except.")
            self._logger.error(traceback.format_exc())
            return False
        finally:
            sleep_after = 0
            if "sleep_after" in self.case_info_dict:
                sleep_after = self.case_info_dict["sleep_after"]


            if not self.properly_executed:
                self._clean_up_when_fail()

            time.sleep(sleep_after)
            return self.properly_executed

    def _execute_http_request(self):
        self._logger.debug("execute ppt share")
        url = Constant.CONFS_URL + "/" + str(self.attach_conf_id) + "/ginfo"
        method = 'POST'
        data = json.dumps({
            "ppt": self.Tager
        })
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url,
                                        name="/pptshare", catch_response=False,
                                        data=data, headers=headers)
        return r

    def _clean_up_when_fail(self):
        """release user source when fail."""
        if self.user_pool.cache_lock.locked():
            self.user_pool.cache_lock.release()
        abnormal_interrupt = False
        if "abnormal_interrupt" in self.case_info_dict:
            abnormal_interrupt = self.case_info_dict["abnormal_interrupt"]

        if abnormal_interrupt:
            self.p_stop_signal.set()
            # False，设置终止整个测试信号
        else:
            pass
