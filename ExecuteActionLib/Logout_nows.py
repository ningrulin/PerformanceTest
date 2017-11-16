# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
import logging
import time
import traceback
from public.ConstantSet import Constant
from public.HttpClient import HttpClient
import json


class LogoutNoWSAction(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.executor_phone_num = None
        self._logger = logging.getLogger(log_name)
        self._logger_ar = logging.getLogger("AllResult")
        self.properly_executed = False

    def _execute_action(self):
        try:
            # 出现异常或者失败的情况是否终止当前任务的标志
            self.abnormal_interrupt = False
            if "abnormal_interrupt" in self.case_info_dict:
                self.abnormal_interrupt = self.case_info_dict["abnormal_interrupt"]

            self.user_pool.cache_lock.acquire()
            self.executor_phone_num = self.user_pool.online_user_phone_num_list.pop()
            self.user_pool.cache_lock.release()

            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]

            sleep_after = 0
            if "sleep_after" in self.case_info_dict:
                sleep_after = self.case_info_dict["sleep_after"]
            # 获取userset中的groupID
            r = self._execute_http_request()
            self._logger.info("Sleep %s s after action!" % sleep_after)
            time.sleep(sleep_after)
            if r.status_code == 200:
                self.user_pool.cache_lock.acquire()
                self.user_pool.offline_user_phone_num_list.appendleft(self.executor_phone_num)
                self.user_pool.cache_lock.release()
                self._logger.info("Logout success!")
                self._logger_ar.debug("Logout success!")
                self.properly_executed = True
                return True
            else:
                self._logger_ar.debug("Logout fail!")
                return False
        except:
            self._logger.warning("Return False because of except.")
            self._logger_ar.debug("Logout except!")
            self._logger.warning(traceback.format_exc())

        finally:
            if not self.properly_executed:
                self._clean_up_when_fail()


    def _execute_http_request(self):
        self.exe_success = False
        self._logger.info("execute logout")
        url = Constant.CAS_HOST + "/mhauth/logout"
        data = {
            "refresh_token": self.executor_obj.user_info_dict["refresh_token"]
        }
        data = json.dumps(data)

        headers = {"Host": Constant.HOST_NAME,
                   "authorization": self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        method = "POST"
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name="/mhauth/logout", catch_response=False, headers=headers, data = data)
        self.executor_obj.ws_client.stop()
        return r

    def _clean_up_when_fail(self):
        if self.user_pool.cache_lock.locked():
            self.user_pool.cache_lock.release()

        self.user_pool.cache_lock.acquire()
        if self.executor_phone_num not in self.user_pool.online_user_phone_num_list:
            self.user_pool.online_user_phone_num_list.appendleft(self.executor_phone_num)
            if self.executor_phone_num in self.user_pool.offline_user_phone_num_list:
                self.user_pool.offline_user_phone_num_list.delete(self.executor_phone_num)
        self.user_pool.cache_lock.release()

        if self.abnormal_interrupt:
            self.p_stop_signal.set()
            # False，设置终止整个进程信号
        else:
            pass
