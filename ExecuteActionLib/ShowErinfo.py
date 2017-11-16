# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
import logging
import time
import json
import traceback
from public.ConstantSet import Constant
from public.HttpClient import HttpClient
import random


class ShowErinfoAction(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.executor_phone_num = None
        self.properly_executed = False
        self.check_result = False
        self._logger = logging.getLogger(log_name)
        self._logger_ar = logging.getLogger("AllResult")

    def _execute_action(self):
        try:
            if "check_result" in self.case_info_dict:
                self.check_result = self.case_info_dict["check_result"]

            if self.check_result:
                self.user_pool.cache_lock.acquire()
                self.executor_phone_num = self.user_pool.online_user_phone_num_list.pop()
                self.user_pool.cache_lock.release()
            else:
                self.executor_phone_num = random.choice(self.user_pool.online_user_phone_num_list)

            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]

            http_response = self._execute_http_request()
            if http_response.status_code == 200:
                self._logger.info("Shower success!")
                self._logger_ar.debug("Shower 200")
                self.properly_executed = True
                return True
            else:
                self._logger.info("Shower Fail!")
                self._logger_ar.debug("Shower fail! http == " + str(http_response.status_code))
                return False
        except:
            self._logger.warning("Return False because of except.")
            self._logger_ar.debug("Shower except")
            self._logger.warning(traceback.format_exc())
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
        url = Constant.HOST + "/dimension/dec/dimension"
        method = 'POST'
        data = {
                 "id": str(self.executor_obj.user_info_dict["userID"])
                }
        data = json.dumps(data)
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name=None, catch_response=False, headers=headers,
                                        data=data)
        self._logger.debug("aqf: r.t" + str(r.text))
        self._logger.debug("aqf: r.r" + str(r.status_code))
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
            self.user_pool.cache_lock.acquire()
            if self.executor_phone_num not in self.user_pool.online_user_phone_num_list:
                self.user_pool.online_user_phone_num_list.appendleft(self.executor_phone_num)
            self.user_pool.cache_lock.release()
