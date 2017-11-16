# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
import logging
import time
import json
import traceback
import random
import requests
from public.ConstantSet import Constant
from public.HttpClient import HttpClient
from requests.exceptions import ConnectionError


class ApplyFloorAction(ExecuteAction):
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

            self._logger.info("self.user_pool.in_conf_mem_phone_num_list:" +
                              str(self.user_pool.in_conf_mem_phone_num_list))
            # 在in_conf_mem_phone_num_list中随机选取一个元素
            if self.check_result:
                self.user_pool.cache_lock.acquire()
                self.executor_phone_num = self.user_pool.in_conf_mem_phone_num_list.pop()
                self.user_pool.cache_lock.release()
            else:
                # 在conf_mem_phone_num_list中随机选取一个元素
                self.executor_phone_num = random.choice(self.user_pool.in_conf_mem_phone_num_list)

            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]
            self.is_aff = self.executor_obj.is_aff
            self.attach_conf_id = self.executor_obj.attach_conf_id
            self.conf_obj = self.user_pool.conf_id_obj_dict[self.attach_conf_id]
            self.conf_mid_map = self.conf_obj.mid_map
            self._logger.debug("self.conf_mid_map" + str(self.conf_mid_map))
            self._logger.debug("self.executor_obj.user_info_dict" + str(self.executor_obj.user_info_dict["userID"]))
            self.executor_mid = self.conf_mid_map[str(self.executor_obj.user_info_dict["userID"])]
            self._logger.debug("self.executor_mid" + str(self.executor_mid))

            http_response = self._execute_http_request()
            # 返回204表示举手成功，返回400表示已经在拒收了，重复举手。
            if http_response.status_code == 200 :
                self._logger.info("ApplyFloor Success!")
                if self.check_result:
                    if self.check_aff_info():
                        self.user_pool.cache_lock.acquire()
                        self.user_pool.in_conf_mem_phone_num_list.appendleft(self.executor_phone_num)
                        self.user_pool.cache_lock.release()
                        self._logger_ar.debug("execute ApplyFloor: check result success! http.status_code == 200")
                        self.properly_executed = True
                        return True
                    else :
                        self.user_pool.cache_lock.acquire()
                        self.user_pool.in_conf_mem_phone_num_list.appendleft(self.executor_phone_num)
                        self.user_pool.cache_lock.release()
                        self._logger_ar.debug("execute ApplyFloor: check result error! http.status_code == 200")
                        return False
                self._logger_ar.debug("execute ApplyFloor: http.status_code == 200")
                self.properly_executed = True
                return True
            else:
                self._logger.error("ApplyFloor http Fail!")
                if self.check_result:
                    self._logger_ar.debug("execute ApplyFloor: check result fail! http.status_code == "+ str(http_response.status_code))
                self._logger_ar.debug("execute ApplyFloor: http.status_code == " + str(http_response.status_code))
                return False
        except:
            self._logger.error("Return False because of except.")
            self._logger_ar.debug("execute ApplyFloor except")
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
        self._logger.info("execute aff_member")
        url = Constant.CONFS_URL + "/" + str(self.attach_conf_id) + "/aff"
        method = 'PUT'
        # 使用把参数列表中的groupshareid
        data = json.dumps({
            "applyFloor": not self.is_aff
        })
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name="/cxf/confs3/confIDXXX/aff",
                                        catch_response=False, headers=headers,
                                        data=data)
        return r

    def check_aff_info(self):
        server_aff_data_flag, server_aff_data = self.query_confs3_AFS()
        self._logger.debug("aqf:dddd" + str(server_aff_data_flag))
        self._logger.debug("aqf:dddd" + str(server_aff_data))
        if not server_aff_data_flag:
            self._logger.error("error:"+str(server_aff_data))
            return False

        except_aff_status = not self.is_aff
        self._logger.debug("aqf:dddd" + str(except_aff_status))
        now_aff_status = self.check_in_aff_list(server_aff_data)
        if except_aff_status == now_aff_status:
            self._logger.info("check aff info success, "+"mid:"+str(self.executor_mid)
                              + " phone_num:"+str(self.executor_phone_num)
                              + " except_aff_status:"+str(except_aff_status)
                              + " now_aff_status:"+str(now_aff_status))
            return True
        else:
            self._logger.info("check aff info failed, " + "mid:" + str(self.executor_mid)
                              + " phone_num:" + str(self.executor_phone_num)
                              + " except_aff_status:" + str(except_aff_status)
                              + " now_aff_status:" + str(now_aff_status))
            return False

    def check_in_aff_list(self,server_aff_data):
        aff_list = []
        if "afs" in server_aff_data:
            aff_list = json.loads(server_aff_data)["afs"]["afs"]

        afs_status = False
        for afs in aff_list:
            if str(afs["mid"]) == str(self.executor_mid):
                afs_status = True
                break

        if afs_status:
            self._logger.info("MID in the list of hands!")
            return True
        else :
            self._logger.info("MID is not in the list of hands!")
            return False

    def query_confs3_AFS(self):
        try:
            self._logger.info("execute query_conference")
            url = Constant.CONFS_URL + "/" + self.attach_conf_id + "?param=AFS"

            headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                       "Content-Type": "application/json; charset=utf-8"}

            r = requests.get(url, headers=headers)
            self._logger.info("aaaaafy:" + str(r.text))
            if int(r.status_code) == 200:
                return True, r.text
            elif int(r.status_code) == 404:
                return False, "no conf_id"
            else:
                return False, r.status_code
        except ConnectionError as e:
            self._logger.error(e)
            return False, "ConnectionError"

    def _clean_up_when_fail(self):
        """release user source when fail."""
        if self.user_pool.cache_lock.locked():
            self.user_pool.cache_lock.release()

        if self.check_result:
            if self.executor_phone_num not in self.user_pool.in_conf_mem_phone_num_list:
                self.user_pool.cache_lock.acquire()
                self.user_pool.in_conf_mem_phone_num_list.appendleft(self.executor_phone_num)
                self.user_pool.cache_lock.release()
        abnormal_interrupt = False
        if "abnormal_interrupt" in self.case_info_dict:
            abnormal_interrupt = self.case_info_dict["abnormal_interrupt"]

        if abnormal_interrupt:
            self.p_stop_signal.set()
            # False，设置终止整个测试信号
        else:
            pass
