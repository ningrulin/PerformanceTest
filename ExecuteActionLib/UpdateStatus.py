# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
import logging
import time
import json
import traceback
import random
from public.ConstantSet import Constant
from public.HttpClient import HttpClient


class UpdateStatusAction(ExecuteAction):
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

    def _execute_action(self):
        try:
            self.user_pool.cache_lock.acquire()
            if self.check_result:
                self.executor_phone_num = self.user_pool.in_conf_mem_phone_num_list.pop()
            else:
                # 在in_conf_mem_phone_num_list中随机选取一个元素
                self.executor_phone_num = random.choice(self.user_pool.in_conf_mem_phone_num_list)
            self.user_pool.cache_lock.release()
            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]
            self.attach_conf_id = self.executor_obj.attach_conf_id
            self.conf_obj = self.user_pool.conf_id_obj_dict[self.attach_conf_id]
            self.conf_mid_map = self.conf_obj.mid_map
            self.executor_userID = str(self.executor_obj.user_info_dict["userID"])

            http_response = self._execute_http_request()

            if http_response.status_code == 200:
                self.user_pool.cache_lock.acquire()
                self.user_pool.conf_mem_phone_num_list.appendleft(self.executor_phone_num)
                self.user_pool.cache_lock.release()
                self._logger.info("UpdateStatus success!")
                if self.check_result:
                    # 检查选看关系失败处理
                    if not self.check_status_info():
                        self._logger.error("Check Status result fail!")
                        return False

                    # 检查选看关系成功处理
                    self.user_pool.cache_lock.acquire()
                    self.user_pool.in_conf_mem_phone_num_list.appendleft(self.executor_phone_num)
                    self.user_pool.cache_lock.release()
                self.properly_executed = True
                return True
            else:
                self._logger.error("UpdateStatus Fail!")
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
        self._logger.info("execute updatestatus")
        url = Constant.CONFS_URL + "/" + str(self.attach_conf_id) + "/members/status"
        method = 'POST'
        # 使用把参数列表中的groupshareid
        data = json.dumps([{
            "mid": self.conf_obj.mid_map[self.executor_userID],
            "vs": 2}])
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url,
                                        name="/members/status", catch_response=False, headers=headers,
                                        data=data)
        return r

    def check_status_info(self):
        """
        检查成员status信息，暂未处理，预留位置
        :return:
        """
        pass

    def _clean_up_when_fail(self):
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
            if self.executor_phone_num not in self.user_pool.in_conf_mem_phone_num_list:
                self.user_pool.in_conf_mem_phone_num_list.appendleft(self.executor_phone_num)
            self.user_pool.cache_lock.release()
