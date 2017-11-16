# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
import logging
import json
import copy
import time
import random
import traceback
from public.ConstantSet import Constant
from public.HttpClient import HttpClient


class AddMem2ConfNOSIppAction(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.attach_conf_id = None
        self.conf_obj = None
        self.executor_phone_num = None
        self.group_shareID = None
        self.properly_executed = False
        self.check_result = False
        self._logger = logging.getLogger(log_name)
        self._logger_cn = logging.getLogger("Count")

        self.mss_data = None

    def _execute_action(self):
        try:
            if "check_result" in self.case_info_dict:
                self.check_result = self.case_info_dict["check_result"]

            add_mem_num = 1
            if "add_mem_num" in self.case_info_dict:
                add_mem_num = self.case_info_dict["add_mem_num"]
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

            try:
                self.added_mem_list = random.sample(self.conf_obj.out_conf_mem_num_list, add_mem_num)
            except ValueError:
                self._logger.exception("No enough rs.")
                self._logger.exception(traceback.format_exc())
                return False
            self.add_mem_data = []
            for add_mem in self.added_mem_list:
                self.add_mem_data.append({
                    "uid": self.user_pool.user_phone_num_obj_dict[add_mem].user_info_dict["userID"],
                    "name": self.user_pool.user_phone_num_obj_dict[add_mem].user_info_dict["commName"]
                })

            http_response = self._execute_http_request()

            if http_response.status_code == 200:
                self._logger.info("add Mem success!")
                self.properly_executed = True
                return True
            else:
                self._logger.error("add Mem Http Fail!")
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
        self._logger.debug("execute add Mem ")
        url = Constant.CONFS_URL + "/" + str(self.attach_conf_id) + "/members/add"
        method = 'POST'

        data = []  # is a dict list. dict{uid:"",name:""}
        data = json.dumps(data)
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name="/members/add",
                                        catch_response=False, headers=headers, data=data)
        return r

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
