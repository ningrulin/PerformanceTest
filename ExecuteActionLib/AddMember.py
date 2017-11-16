# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
import logging
import time
import json
import copy
import random
import requests
import traceback
from public.ConstantSet import Constant
from public.HttpClient import HttpClient
from requests.exceptions import ConnectionError


class AddMemberAction(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.executor_phone_num = None
        self.group_shareid = None
        self.is_mute = False
        self.properly_executed = False
        self._logger = logging.getLogger(log_name)
        self._logger_cn = logging.getLogger("Count")
        self.check_result = False
        self.attach_conf_id = None
        self.conf_obj = None
        self.conf_mid_map = None
        self.add_mem_phone_num = None
        self.mute_mid = None
        self.opp_mem_num = None
        self.opp_uid = None
        self.opp_name = None
        self.opp_mid = None
        self.chair_obj = None
        self.opp_mem_obj = None
        self.flag = False
        self._logger_ar = logging.getLogger("AllResult")


    def _execute_action(self):
        try :
            if "check_result" in self.case_info_dict:
                self.check_result = self.case_info_dict["check_result"]

            self.executor_phone_num = random.choice(self.user_pool.conf_chair_phone_num_list)
            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]
            self.attach_conf_id = self.executor_obj.attach_conf_id

            self.conf_obj = copy.deepcopy(self.user_pool.conf_id_obj_dict[self.attach_conf_id])
            self.conf_mid_map = self.conf_obj.mid_map
            self.add_mem_phone_num = random.choice(self.conf_obj.in_conf_mem_num_list)
            self.chair_obj = self.user_pool.user_phone_num_obj_dict[self.conf_obj.conf_chair_phone_num]

            self.user_pool.cache_lock.acquire()
            self.opp_mem_num = self.user_pool.out_conf_mem_phone_num_list.pop()
            self.user_pool.cache_lock.release()

            self.add_mid = self.conf_mid_map[str(self.user_pool.user_phone_num_obj_dict[self.add_mem_phone_num].user_info_dict["userID"])]

            self.opp_uid = self.user_pool.user_phone_num_obj_dict[self.opp_mem_num].user_info_dict["userID"]
            self.opp_name = self.user_pool.user_phone_num_obj_dict[self.opp_mem_num].user_info_dict["name"]
            self.opp_mid = self.conf_mid_map[str(self.user_pool.user_phone_num_obj_dict[self.opp_mem_num].user_info_dict["userID"])]

            if self.check_result:
                self.opp_mem_obj = self.user_pool.user_phone_num_obj_dict[self.opp_mem_num]
                self.opp_mem_obj.ws_client.add_handler(self._analyze_notify)

            http_response = self._execute_http_request()
            if http_response.status_code == 200:
                if self.check_result:
                    if not self._check_result():
                        self.user_pool.cache_lock.acquire()
                        self.user_pool.out_conf_mem_phone_num_list.appendleft(self.opp_mem_num)
                        self.user_pool.cache_lock.release()
                        self._logger_ar.debug("execute Add: check result error! http.status_code == 200")
                        self.opp_mem_obj = self.user_pool.user_phone_num_obj_dict[self.opp_mem_num]
                        self.opp_mem_obj.ws_client.sub_handler(self._analyze_notify)
                        return False

                    if not self._kick_inconf():
                        self.user_pool.cache_lock.acquire()
                        self.user_pool.in_conf_mem_phone_num_list.appendleft(self.opp_mem_num)
                        self.user_pool.cache_lock.release()
                        self._logger_ar.debug("execute Add: check result success! resove fail! http.status_code == 200")
                    else:
                        self._logger_ar.debug("execute Add: check result success! resove success! http.status_code == 200")
                        self.user_pool.cache_lock.acquire()
                        self.user_pool.out_conf_mem_phone_num_list.appendleft(self.opp_mem_num)
                        self.user_pool.cache_lock.release()

                    self.opp_mem_obj = self.user_pool.user_phone_num_obj_dict[self.opp_mem_num]
                    self.opp_mem_obj.ws_client.sub_handler(self._analyze_notify)
                    self.properly_executed = True
                    return True

                self.user_pool.cache_lock.acquire()
                self.user_pool.out_conf_mem_phone_num_list.appendleft(self.opp_mem_num)
                self.user_pool.cache_lock.release()
                self._logger_ar.debug("execute Add: http.status_code == 200")
                self.properly_executed = True
                return True
            else:
                self._logger.error("Add Fail!")
                if self.check_result:
                    self._logger_ar.debug("execute Add: check result fail! http.status_code == " + str(http_response.status_code))

                self._logger_ar.debug("execute Add: http.status_code == " + str(http_response.status_code))
                return False
        except:
            self._logger.error("Return False because of except.")
            self._logger_ar.debug("execute Add: except")
            self._logger.error(traceback.format_exc())
            return False
        finally:

            self._logger.debug("in_conf_mem_num_list: " + str(self.conf_obj.in_conf_mem_num_list))
            self._logger.debug("out_conf_mem_num_list: " + str(self.conf_obj.out_conf_mem_num_list))
            sleep_after = 0

            if "sleep_after" in self.case_info_dict:
                sleep_after = self.case_info_dict["sleep_after"]
            if not self.properly_executed:
                self._clean_up_when_fail()
            time.sleep(sleep_after)
            return self.properly_executed

    def _execute_http_request(self):
        self._logger.info("execute add_member")
        url = Constant.CONFS_URL + "/" + str(self.attach_conf_id) + "/members/add"
        method = 'POST'
        # 使用把参数列表中的groupshareid
        data = [{
                "uid": self.opp_uid,
                "name": self.opp_name
            },]
        data = json.dumps(data)
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name="/members/mute",
                                        catch_response=False, headers=headers,
                                        data=data)
        return r

    def _clean_up_when_fail(self):

        if self.user_pool.cache_lock.locked():
            self.user_pool.cache_lock.release()

        if self.opp_mem_num not in self.user_pool.out_conf_mem_phone_num_list:
            self.user_pool.cache_lock.acquire()
            self.user_pool.out_conf_mem_phone_num_list.appendleft(self.opp_mem_num)
            self.user_pool.cache_lock.release()

        abnormal_interrupt = False
        if "abnormal_interrupt" in self.case_info_dict:
            abnormal_interrupt = self.case_info_dict["abnormal_interrupt"]

        if abnormal_interrupt:
            self.p_stop_signal.set()
            # False，设置终止整个测试信号
        else:
            pass

    def _check_result(self):
        server_affdata_flag = False
        time.sleep(50)
        if self.flag:
            server_affdata_flag, server_affdata = self._query_confs3_DETAIL()
        if not server_affdata_flag:
            return False
        user_list = {}
        user_list =json.loads(server_affdata)[0]
        self._logger.debug("aqf: print name server_affdata" + str(server_affdata))
        self._logger.debug("aqf: print name self.opp_mid" + str(self.opp_mid))
        if int(user_list["mid"]) == int(self.opp_mid) and user_list["ol"]:
            return True
        else:
            return False

    def _analyze_notify(self, **kwargs):
        if "message" in kwargs:
            json_data = json.loads(kwargs["message"])
            event = json_data.get("event", {})
            event_name = event.get("name", "")
            self._logger.debug("aqf: print name:" + str(event.get("name", "")))
            self._logger.debug("aqf: print event_body:" + str(event.get("body", [])))

            if event_name == "mx.conf3.invite" :
                if "body" in event:
                    event_body = event.get("body", {})
                else:
                    event_body = event

                if event_body.get("id", "") == str(self.attach_conf_id):
                    url = Constant.CONFS_URL + "/" + str(self.attach_conf_id) + "/callme"
                    basic_token = None
                    if "basic_token" in kwargs:
                        basic_token = kwargs["basic_token"]
                    headers = {'authorization': basic_token,
                               "Content-Type": "application/json; charset=utf-8"}
                    data = {"device": "ios"}
                    data = json.dumps(data)
                    r = requests.post(url, headers=headers, data=data)
                    r.close()
                    if r.status_code == 204:
                        self.flag = True
                    else:
                        self.flag = False
                else:
                    pass
            else:
                pass
        else:
            pass


    def _query_confs3_DETAIL(self):
        try:
            self._logger.info("execute query_detail")
            data = [self.opp_mid,]
            data = json.dumps(data)
            url = Constant.CONFS_URL + "/" + self.attach_conf_id + "/members"
            headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                       "Content-Type": "application/json; charset=utf-8"}

            r = requests.post(url, headers=headers,data = data)
            r.close()
            if int(r.status_code) == 200:
                return True, r.text
            elif int(r.status_code) == 404:
                return False, "no conf_id"
            else:
                return False, r.status_code
        except ConnectionError as e:
            print e
            return False, "ConnectionError"

    def _kick_inconf(self):

        url = Constant.CONFS_URL + "/" + str(self.attach_conf_id) + "/members/kick"
        method = 'POST'
        # 使用把参数列表中的groupshareid
        data = [self.opp_mid, ]
        data = json.dumps(data)
        headers = {'authorization': self.chair_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        r = requests.post(url=url, headers=headers, data=data)
        r.close()

        if int(r.status_code) == 200:
            return True
        else:
            return False