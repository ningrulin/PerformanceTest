# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
import logging
import time
import json
import traceback
from public.ConstantSet import Constant
from public.HttpClient import HttpClient

class JoinGroupByIDAction(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.executor_phone_num = None
        self.group_shareid =None
        self._logger = logging.getLogger(log_name)

    def _execute_action(self):
        try:
            # 出现异常或者失败的情况是否终止当前任务的标志
            abnormal_interrupt = True
            if "abnormal_interrupt" in self.case_info_dict:
                abnormal_interrupt = self.case_info_dict["abnormal_interrupt"]

            self.user_pool.cache_lock.acquire()
            self.executor_phone_num = self.user_pool.group_mem_phone_num_list.pop()
            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]
            group_id = self.executor_obj.attach_group_id
            self.group_shareid = self.user_pool.group_id_obj_dict[group_id]._share_id
            self.user_pool.cache_lock.release()
            sleep_after = 0
            if "sleep_after" in self.case_info_dict:
                sleep_after = self.case_info_dict["sleep_after"]
            r = self._execute_http_request()

            if r.status_code == 200:
                self.user_pool.cache_lock.acquire()
                self.user_pool.group_mem_phone_num_list.appendleft(self.executor_phone_num)
                self.user_pool.cache_lock.release()
                self._logger.info("JoinGroupByID success!")
                time.sleep(sleep_after)
                return True
            else:
                self.user_pool.cache_lock.acquire()
                self.user_pool.group_mem_phone_num_list.appendleft(self.executor_phone_num)
                self.user_pool.cache_lock.release()
                self._logger.info("JoinGroupByID Fail!")
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
        url = Constant.JOIN_GROUP_BY_ID_URL
        method = 'POST'
        # 使用把参数列表中的groupshareid
        data = json.dumps({'shareid': str(self.group_shareid )})
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}

        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name=None, catch_response=False, headers=headers,
                                        data=data)
        self._logger.info(r.text)
        return r