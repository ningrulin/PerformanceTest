# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
import logging
import time
import json
import traceback
from public.ConstantSet import Constant
from public.HttpClient import HttpClient

class V3SearchContactInfoAction(ExecuteAction):
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

            self.user_pool.cache_lock.acquire()
            self.executor_phone_num = self.user_pool.online_user_phone_num_list.pop()
            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]
            self.user_pool.cache_lock.release()
            sleep_after = 0
            if "sleep_after" in self.case_info_dict:
                sleep_after = self.case_info_dict["sleep_after"]
            # 获取userset中的groupID
            http_response = self._execute_http_request()

            if http_response.status_code == 200:
                self.user_pool.cache_lock.acquire()
                self.user_pool.online_user_phone_num_list.appendleft(self.executor_phone_num)
                self.user_pool.cache_lock.release()
                self._logger.info("GetUserInfo success!")
                self._logger.info("Sleep %s s after action!" % sleep_after)
                time.sleep(sleep_after)
                return True
            else:
                self.user_pool.cache_lock.acquire()
                self.user_pool.online_user_phone_num_list.appendleft(self.executor_phone_num)
                self.user_pool.cache_lock.release()
                self._logger.info("GetUserInfo Fail!")
                self._logger.info("Sleep %s s after action!" % sleep_after)
                if abnormal_interrupt:
                    self.p_stop_signal.set()
                    # False，设置终止整个进程信号
                time.sleep(sleep_after)
                return False

        except:
            if self.user_pool.cache_lock.locked():
                self.user_pool.cache_lock.release()
            self._logger.warning("GetUserInfo Return False because of except.")
            #todo 需不需要放回用户列表中取
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
        self._logger.info("execute get_user_info")
        url = Constant.HTTP_HOST_V3 + "/mhuser/search/user"
        data = {
            ""
        }
        method = 'POST'
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name="/mhuser/search/user", catch_response=False, headers=headers)
        print r.text
        self._logger.debug("aqf" + self.executor_obj.user_info_dict["userPhoneNum"])
        self._logger.debug("aqf" + str(self.executor_obj.user_info_dict["basicToken"]))
        self._logger.debug("aqf" + str(r.status_code))
        mod_user_info_dict = json.loads(r.text)
        mod_user_info_dict['userID'] = str(mod_user_info_dict['user']['userid'])
        self.executor_obj.mod_user_info_dict(mod_user_info_dict)
        # print "1234567890" + str(action_executor.mod_user_info_dict["name"]) + str(r.status_code)
        return r