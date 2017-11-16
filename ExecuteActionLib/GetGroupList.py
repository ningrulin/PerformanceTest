# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
import logging
import time
import json
import traceback
from public.ConstantSet import Constant
from public.HttpClient import HttpClient


class GetGroupListAction(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.executor_phone_num = None
        self._logger = logging.getLogger(log_name)

    def _execute_action(self):
        try:
            # 出现异常或者失败的情况是否终止当前任务的标志
            abnormal_interrupt = True
            if "abnormal_interrupt" in self.case_info_dict:
                abnormal_interrupt = self.case_info_dict["abnormal_interrupt"]
            sleep_after = 0
            if "sleep_after" in self.case_info_dict:
                sleep_after = self.case_info_dict["sleep_after"]

            self.user_pool.cache_lock.acquire()
            self.executor_phone_num = self.user_pool.online_user_phone_num_list.pop()
            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]
            self.user_pool.cache_lock.release()

            http_response = self._execute_http_request()

            if http_response.status_code == 200:
                self.user_pool.cache_lock.acquire()
                self.user_pool.online_user_phone_num_list.appendleft(self.executor_phone_num)
                self.user_pool.cache_lock.release()
                self._logger.info("GetGroupList success!")
                self._logger.info("Sleep %s s after action!" % sleep_after)
                time.sleep(sleep_after)
                return True
            else:
                self.user_pool.cache_lock.acquire()
                self.user_pool.online_user_phone_num_list.appendleft(self.executor_phone_num)
                self.user_pool.cache_lock.release()
                self._logger.info("GetGroupList Fail!")
                self._logger.info("Sleep %s s after action!" % sleep_after)
                if abnormal_interrupt:
                    self.p_stop_signal.set()
                    # False，设置终止整个进程信号
                time.sleep(sleep_after)
                return False
        except:
            if self.user_pool.cache_lock.locked():
                self.user_pool.cache_lock.release()
            self._logger.warning("Return False because of except.")
            self._logger.warning(traceback.format_exc())
            # 出现异常，设置终止整个进程信号
            abnormal_interrupt = True
            if "abnormal_interrupt" in self.case_info_dict:
                abnormal_interrupt = self.case_info_dict["abnormal_interrupt"]
            if abnormal_interrupt:
                self.p_stop_signal.set()
                # False，设置终止整个进程信号
            return False

    def _execute_http_request(self):
        url = Constant.GET_GROUP_LIST_URL
        method = 'POST'
        data = {'id': str(self.executor_obj.user_info_dict["userID"])
                }
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        http_response = execute_http_client.request(method=method, url=url,
                                                    name=None, catch_response=False, headers=headers,
                                                    data=json.dumps(data))
        return http_response
