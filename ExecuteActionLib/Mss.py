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

class MssAction(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.attach_conf_id = None
        self.conf_obj = None
        self.executor_phone_num = None
        self.group_shareid =None
        self.properly_executed =  False
        self.check_result = False
        self._logger = logging.getLogger(log_name)
        self._logger_cn = logging.getLogger("Count")
        self._logger_ar = logging.getLogger("AllResult")
        self.mid = None

        self.mss_data = None

    def _execute_action(self):
        try:
            if "check_result" in self.case_info_dict:
                self.check_result = self.case_info_dict["check_result"]

            self._logger.debug("aqf: print " + str(self.user_pool.in_conf_mem_phone_num_list))

            if self.check_result:
                self.user_pool.cache_lock.acquire()
                self.executor_phone_num = self.user_pool.in_conf_mem_phone_num_list.pop()
                self.user_pool.cache_lock.release()
            else:
                # 在in_conf_mem_phone_num_list中随机选取一个元素
                self.executor_phone_num = random.choice(self.user_pool.in_conf_mem_phone_num_list)

            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]
            self.attach_conf_id = self.executor_obj.attach_conf_id
            self.conf_obj = self.user_pool.conf_id_obj_dict[self.attach_conf_id]
            self.conf_mid_map = self.conf_obj.mid_map

            self.mid = self.conf_mid_map[
                str(self.user_pool.user_phone_num_obj_dict[self.executor_phone_num].user_info_dict["userID"])]

            http_response = self._execute_http_request()

            if http_response.status_code == 200:
                self.executor_obj.conf_mss_v += 1
                self._logger.info("Mss success!")
                if self.check_result:
                    # 检查选看关系失败处理
                    if not self.check_msss_info():
                        self._logger.error("Check MSS result fail!")
                        self._logger_ar.debug("execute mss_member: check result error! http.status_code == 200")
                        return False
                    else:
                        # 检查选看关系成功处理
                        self.user_pool.cache_lock.acquire()
                        self.user_pool.in_conf_mem_phone_num_list.appendleft(self.executor_phone_num)
                        self.user_pool.cache_lock.release()
                        self._logger_ar.debug("execute mss_member: check result success! http.status_code == 200")
                        self.properly_executed = True
                        return True
                self.properly_executed = True
                self._logger_ar.debug("execute mss_member: http.status_code == 200")
                return True
            else:
                self._logger.error("Mss Http Fail!")
                if self.check_result:
                    self._logger_ar.debug("execute mss_member: check result fail! http.status_code == " + str(http_response.status_code))
                self._logger_ar.debug("execute mss_member: http.status_code == " + str(http_response.status_code))
                return False
        except:
            self._logger.error("Return False because of except.")
            self._logger_ar.debug("execute mss_member: except")
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
        self._logger.debug("execute mss_member")
        url = Constant.CONFS_URL + "/" +str(self.attach_conf_id) + "/members/mss/" + str(self.mid)  # v3
        # url = Constant.CONFS_URL + str(self.attach_conf_id) + "/mss" #v2
        method = 'POST'
        self.mss_data = self.random_mss_data2(self.executor_obj.user_info_dict["userID"])
        # self.mss_data = self.random_mss_data(self.executor_obj.user_info_dict["userID"])
        data = {
            "v": self.executor_obj.conf_mss_v+1,
            "mss": self.mss_data
        }
        data = json.dumps(data)
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name="/members/mss", catch_response=False, headers=headers,
                                        data=data)
        self._logger_cn.debug("VVVVVIP"+str(self.executor_phone_num)+"V"+str(self.conf_mid_map)+"V"+str(data))
        return r

    def random_mss_data(self,userID):
        mss_data = []
        copy_mid_map = copy.deepcopy(self.conf_mid_map)
        del copy_mid_map[str(userID)]
        if len(copy_mid_map)>4:
            select_num = 5
        else:
            select_num = len(copy_mid_map)
        choice_id_list = random.sample(copy_mid_map, select_num)
        for user_id in choice_id_list[:-1]:
            mss_data.append({"selected": int(copy_mid_map[user_id]),
                            "label": 2,  #label对于虚拟用户无意义，携带同样的
                            "level": 1})
        mss_data.append({"selected": int(copy_mid_map[choice_id_list[-1]]),
                            "label": 2,  #label对于虚拟用户无意义，携带同样的
                            "level": 1})

        return mss_data

    def random_mss_data2(self, userID):
        mss_data = []
        label_list = [0, 1, 2, 3, 4]
        copy_mid_map = copy.deepcopy(self.conf_mid_map)
        del copy_mid_map[str(userID)]
        if len(copy_mid_map) > 4:
            select_num = 5
        else:
            select_num = len(copy_mid_map)
        choice_id_list = random.sample(copy_mid_map, select_num)
        for user_id in choice_id_list[:-1]:
            label_num = random.choice(label_list)
            label_list.remove(label_num)
            mss_data.append({"selected": int(copy_mid_map[user_id]),
                            "label": label_num,  #label对于虚拟用户无意义，携带同样的
                            "level": 1})
        level_list = [1, 4]
        mss_data.append({"selected": int(copy_mid_map[choice_id_list[-1]]),
                            "label": random.choice(label_list),  #label对于虚拟用户无意义，携带同样的
                            "level": random.choice(level_list)})
        self._logger.debug("MSS DATA:" + str(mss_data))
        return mss_data

    def check_msss_info(self):
        server_msssdata_flag, server_msssdata = self.get_my_mss(self.conf_mid_map[
                                                                    str(self.executor_obj.user_info_dict["userID"])])
        if not server_msssdata_flag:
            self._logger.error("Get picking relationship failed!"+str(server_msssdata))
            return False
        self._logger.error("Mss check,mss in server:" + str(server_msssdata) +
                           "  Except mss:" + str(self.mss_data))
        if len(server_msssdata) != 5:
            self._logger.info("Server selection relationship is not enough!")
            return False
        for msss_i in server_msssdata:
            if msss_i not in self.mss_data:
                self._logger.error("Mss check is completed, choose to see the relationship is inconsistent!"
                                   +str(self.executor_phone_num))
                #self._logger_cn.info("选看关系检查完成，选看关系不一致！"+str(self.executor_phone_num))
                return False

        self._logger.info("Mss check is completed, is same with server.")
        return True

    def query_confs2(self):
        try:
            headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                       "Content-Type": "application/json; charset=utf-8"}
            URL = Constant.HOST +"/cxf/confs2/" + self.attach_conf_id
            r = requests.get(URL, headers=headers)
            r.close()
            self._logger.info(URL+",statuse_code:"+str(r.status_code)+
                              " r.text:"+str(r.text))
            self._logger_cn.info(URL+",statuse_code:"+str(r.status_code)+
                              " r.text:"+str(r.text))

            if int(r.status_code) == 200:
                return True, r.text
            elif int(r.status_code) == 404:
                return False, "no conf_id"
            else:
                return False, r.status_code
        except ConnectionError as e:
            print e
            return False, "ConnectionError"

    def get_my_mss(self, user_mid):
        flagG, rText = self.query_confs2()
        if not flagG:
            return False, "No Conf_id"
        memberJson = json.loads(rText)["members"]
        memNum = len(memberJson)
        memberList = memberJson.items()

        for i in range(memNum):
            if memberList[i][1]["conferMemberID"] == user_mid:
                return True, memberList[i][1]["msss2"]

        return False, "No mid"

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
