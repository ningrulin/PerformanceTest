# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
from SipOperation.SipCall import *
from SipOperation.SipRegister import *
from public.ConstantSet import Constant
from public.HttpClient import HttpClient
from public.ConferenceInfo import ConferenceInfo
import logging
import threading
import time
import copy
import json
import requests
import traceback
import random
import uuid



class CreateConf2Action(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.chairman_phone_num = None
        self.group_obj = None
        self.conf_id = None
        self.conf_mid_map = {}
        self.all_in_conf_mem_info_dict = []
        self.conf_mem_phone_num_list = []
        self.in_conf_mem_sip_number_list = []
        self.all_in_conf_mem_sip_number_list = []
        self.all_in_conf_mem_phone_number_list = []
        self.action_resource_lock = threading.Lock()
        self.received_call_notify_num_list = []
        self.properly_executed = False
        self._logger = logging.getLogger(log_name)
        self._logger_ar = logging.getLogger("AllResult")

    def _execute_action(self):
        try:
            reg_callee_caps = 10
            if "reg_callee_caps" in self.case_info_dict:
                reg_callee_caps = self.case_info_dict["reg_callee_caps"]

            self.only_self = False
            if "only_self" in self.case_info_dict:
                self.only_self = self.case_info_dict["only_self"]

            self.user_pool.cache_lock.acquire()
            self.conf_group_id = self.user_pool.group_id_list.pop()
            self.user_pool.cache_lock.release()

            self._logger.debug("this group_id is: " + str(self.conf_group_id))
            self._logger.debug("self.user_pool.group_id_list: " + str(self.user_pool.group_id_list))

            self.group_obj = self.user_pool.group_id_obj_dict[self.conf_group_id]
            self.chairman_phone_num = self.group_obj.group_owner_phone_num
            self._logger.debug("aqf print chair phone num" + str(self.chairman_phone_num))
            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num]

            self.conf_mem_phone_num_list = copy.deepcopy(self.group_obj.group_mem_phone_num_list)
            self.conf_all_mem_phone_num_list = copy.deepcopy(self.conf_mem_phone_num_list)
            self.conf_all_mem_phone_num_list.append(self.chairman_phone_num)

            self.in_conf_mem_phone_num_list = []
            self.out_conf_mem_phone_num_list = self.conf_mem_phone_num_list

            self.all_in_conf_mem_phone_number_list = copy.deepcopy(self.in_conf_mem_phone_num_list)
            self.all_in_conf_mem_phone_number_list.append(self.chairman_phone_num)
            # 主席的sip_number
            conf_chairman_sip_number = str(
                self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num].user_info_dict["userID"]) + "00"
            """# 临时集群环境使用的sip号：
            conf_chairman_sip_number = str(
                int(str(self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num].user_info_dict["userPhoneNum"])[
                    1:12])- 11525100001 + 10010000019) + "00"  """
            # 所有会议成员的sip_number 不包括主席
            for in_conf_mem_phone_num in self.in_conf_mem_phone_num_list:
                conf_mem_sip_number = str(
                    self.user_pool.user_phone_num_obj_dict[in_conf_mem_phone_num].user_info_dict["userID"]) + "00"
                # 临时集群环境使用的sip号：
                """conf_mem_sip_number = str(
                    int(str(
                        self.user_pool.user_phone_num_obj_dict[in_conf_mem_phone_num].user_info_dict["userPhoneNum"])[
                        1:12])- 11525100001 + 10010000019) + "00" """
                # 所有会议成员的sip_number 不包括主席
                self.in_conf_mem_sip_number_list.append(conf_mem_sip_number)
                mem_info_dict = {
                    "uid": self.user_pool.user_phone_num_obj_dict[in_conf_mem_phone_num].user_info_dict["userID"],
                    "name": self.user_pool.user_phone_num_obj_dict[in_conf_mem_phone_num].user_info_dict["commName"]}

                # 发起会议接口需要携带所有会议成员（包括主席）的信息
                self.all_in_conf_mem_info_dict.append(mem_info_dict)

            # 所有会议成员的sip_number 包括主席
            self.all_in_conf_mem_sip_number_list = copy.deepcopy(self.in_conf_mem_sip_number_list)
            self.all_in_conf_mem_sip_number_list.append(conf_chairman_sip_number)

            chairman_info_dict = {
                "uid": self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num].user_info_dict["userID"],
                "name": self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num].user_info_dict["commName"]}
            self.all_in_conf_mem_info_dict.append(chairman_info_dict)

            in_conf_mem_num = len(self.in_conf_mem_phone_num_list)
            all_in_conf_mem_num = in_conf_mem_num + 1
            sip_reg_callee_timeout = in_conf_mem_num // reg_callee_caps + 3

            UUID = uuid.uuid1()
            # sip 注册，对应会议群中所有成员
            """sip_reg = SipRegisterMap.get_instance().get_sip_register(str(self.conf_group_id)+"_"+str(UUID),SipMqConstants.SIP_SERVER)"""
            sip_reg = SipRegisterMap.get_instance().get_sip_register(
                str(self.conf_group_id) + "_" + str(UUID), SipMqConstants.SIP_REG_SERVER)

            #主叫列表
            caller_sip_number_list = []
            caller_sip_number_list.append(conf_chairman_sip_number)
            self._logger.info("aqf:显示主叫号码："+ str(caller_sip_number_list))

            """sip_reg_flag, caller_port, callee_port = \
                sip_reg.register_users_with_same_config(caller_sip_number_list,
                                                        self.in_conf_mem_sip_number_list,SipMqConstants.SIP_SERVER,
                                                        SipMqConstants.SIP_PASSWORD,reg_callee_caps,sip_reg_callee_timeout)"""
            sip_reg_flag, caller_port, callee_port = \
                sip_reg.register_users_with_same_config(caller_sip_number_list,
                                                        self.in_conf_mem_sip_number_list, SipMqConstants.SIP_REG_SERVER,
                                                        SipMqConstants.SIP_PASSWORD, reg_callee_caps,
                                                        sip_reg_callee_timeout)

            if not sip_reg_flag:
                self._logger.error("sip registration failed!")
                return False

            self._logger.debug("he calling port and the called port are: %s,%s" % (str(caller_port), str(callee_port)))

            # 添加handler 监听是否收到call notify
            for conf_mem_phone_num in self.all_in_conf_mem_phone_number_list:
                comf_mem_obj = self.user_pool.user_phone_num_obj_dict[conf_mem_phone_num]
                comf_mem_obj.ws_client.add_handler(self._analyze_notify)

            r = self._execute_http_request()

            if r.status_code != 200:
                self._logger.warning(str(r.text))
                self._logger.error("Create confs fail!")
                self._logger_ar.debug("execute createconf: check result fail! http.status_code == "+ str(r.status_code))
                return False

            self._logger.info("Create confs success!")
            conf_id = json.loads(r.text)["id"]
            self.conf_id = conf_id

            # 先拉起被叫
            # sip 被叫流程
            # 如果是一个人的会议就不需要被叫流程了
            sipcall = SipCallMap.get_instance().get_sip_call(str(self.conf_group_id)+"_"+str(UUID))

            # 主叫
            if not sipcall.make_call(caller_sip_number_list, str(conf_id),
                                     SipMqConstants.SIP_MEDIA_SERVER, SipMqConstants.SIP_PASSWORD,
                                     caller_port, 1000, 10, 15):
                self._logger.error("Sip caller failed!")
                self._logger_ar.debug(
                    "execute createconf: check result fail! http.status_code == 200")
                return False
            self._logger.info("Sip caller is successful!")

            self._logger.info("aqf:sipp创建会议完成了")
            self._logger.debug("Expected to receive call_notify Quantity:" + str(all_in_conf_mem_num) +
                               " Actually received call_notify Quantity:" + str(len(self.received_call_notify_num_list))+
                               " self.received_call_notify_num_list:" + str(self.received_call_notify_num_list))
            time_out = 100
            while time_out:
                self.action_resource_lock.acquire()
                if len(self.conf_mid_map) == in_conf_mem_num:
                    self.action_resource_lock.release()
                    break
                self.action_resource_lock.release()
                time.sleep(1)
                time_out -= 1
            if len(self.conf_mid_map) < in_conf_mem_num:
                self._logger.warning("len(self.conf_mid_map)"+str(len(self.conf_mid_map)))

            self._logger.warning("self.conf_mid_map" + str(self.conf_mid_map))

            mid_flag, mid = self.get_chair_mid()
            if mid_flag:
                self.conf_mid_map.update(mid)
                self._logger.debug("Get user mid success!")
            else:
                self._logger.error("Get user mid fail!")

            # 去掉handler
            for conf_mem_phone_num in self.all_in_conf_mem_phone_number_list:
                comf_mem_obj = self.user_pool.user_phone_num_obj_dict[conf_mem_phone_num]
                comf_mem_obj.ws_client.sub_handler(self._analyze_notify)

            self._init_mss()  # 初始化选流，需不需要判断结果？暂时不做判断，只做模拟
            self.user_pool.cache_lock.acquire()
            self.group_obj.is_in_conf = True
            self.group_obj.conf_id = conf_id
            conf_obj = ConferenceInfo(self.conf_group_id, conf_id, self.chairman_phone_num,
                                      self.conf_mem_phone_num_list, self.out_conf_mem_phone_num_list,
                                      self.in_conf_mem_phone_num_list, self.conf_mid_map)

            for conf_all_mem_num in self.conf_all_mem_phone_num_list:
                self.user_pool.user_phone_num_obj_dict[conf_all_mem_num].attach_conf_id = conf_id

            self.user_pool.conf_id_list.append(conf_id)
            self.user_pool.conf_mem_phone_num_list.extend(self.conf_mem_phone_num_list)
            self.user_pool.in_conf_mem_phone_num_list.extend(self.in_conf_mem_phone_num_list)
            self.user_pool.out_conf_mem_phone_num_list.extend(self.out_conf_mem_phone_num_list)

            self.user_pool.conf_chair_phone_num_list.append(self.chairman_phone_num)
            self.user_pool.conf_all_mem_phone_num_list.extend(self.conf_all_mem_phone_num_list)

            self.user_pool.conf_id_obj_dict.update({conf_id: conf_obj})
            self._logger.info("self.user_pool.conf_id_list" + str(self.user_pool.conf_id_list))
            self.user_pool.cache_lock.release()

            self.user_pool.cache_lock.acquire()
            self.user_pool.group_id_list.appendleft(self.conf_group_id)
            self.user_pool.cache_lock.release()
            self._logger.debug("The conference was created successfully!")
            self._logger_ar.debug(
                "execute createconf: check result success! http.status_code == 200")
            self.properly_executed = True

        except:
            self._logger.error("Return False because of except.")
            self._logger_ar.debug("execute createconf: check except")
            self._logger.error(traceback.format_exc())

        finally:
            sleep_after = 0
            if "sleep_after" in self.case_info_dict:
                sleep_after = self.case_info_dict["sleep_after"]

            if not self.properly_executed:
                self._clean_up_when_fail()

            time.sleep(sleep_after)
            return self.properly_executed

    def _clean_up_when_fail(self):
        """release user source when fail."""
        if self.user_pool.cache_lock.locked():
            self.user_pool.cache_lock.release()
        abnormal_interrupt = False
        if "abnormal_interrupt" in self.case_info_dict:
            abnormal_interrupt = self.case_info_dict["abnormal_interrupt"]

        if abnormal_interrupt:
            self.p_stop_signal.set()
            # False，设置终止整个进程信号
        else:
            self.user_pool.cache_lock.acquire()

            if self.conf_group_id not in self.user_pool.group_id_list:
                self.user_pool.group_id_list.appendleft(self.conf_group_id)

            if self.conf_id is not None:
                self.user_pool.conf_id_list.remove(self.conf_id)

            if self.conf_id in self.user_pool.conf_id_obj_dict:
                del self.user_pool.conf_id_obj_dict[self.conf_id]

            for in_conf_mem_phone_num in self.in_conf_mem_phone_num_list:
                if in_conf_mem_phone_num in self.user_pool.in_conf_mem_phone_num_list:
                    self.user_pool.in_conf_mem_phone_num_list.remove(in_conf_mem_phone_num)
            for out_conf_mem_phone_num in self.out_conf_mem_phone_num_list:
                if out_conf_mem_phone_num in self.user_pool.out_conf_mem_phone_num_list:
                    self.user_pool.out_conf_mem_phone_num_list.remove(out_conf_mem_phone_num)

            for conf_mem_phone_num in self.conf_mem_phone_num_list:
                if conf_mem_phone_num in self.user_pool.conf_mem_phone_num_list:
                    self.user_pool.conf_mem_phone_num_list.remove(conf_mem_phone_num)
                if conf_mem_phone_num in self.user_pool.conf_all_mem_phone_num_list:
                    self.user_pool.conf_all_mem_phone_num_list.remove(conf_mem_phone_num)
            if self.chairman_phone_num in self.user_pool.conf_chair_phone_num_list:
                self.user_pool.conf_chair_phone_num_list.remove(self.chairman_phone_num)
            if self.chairman_phone_num in self.user_pool.conf_all_mem_phone_num_list:
                self.user_pool.conf_all_mem_phone_num_list.remove(self.chairman_phone_num)

            self.group_obj.is_in_conf = True
            self.group_obj.conf_id = None
            self.user_pool.cache_lock.release()

    def _execute_http_request(self):
        self._logger.info("execute create_one_conference: start aqf********")
        url = Constant.CONFS_URL
        # url = "http://test.meetsoon.net/cxf/confs2"
        method = 'POST'
        # 使用把参数列表中的 groupshareid

        data = {"gid": self.conf_group_id,
                "members": self.all_in_conf_mem_info_dict,
                "systemOpenGroup": "false",
                "onlyself": True
                }
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name="create_conference",
                                        catch_response=False, headers=headers,
                                        data=json.dumps(data))
        return r

    def _analyze_notify(self, **kwargs):
        if "message" in kwargs:
            json_data = json.loads(kwargs["message"])
            body = json_data.get("event", {})
            notify_name = body.get("name", "")
            if notify_name == "mx.conf.conf_call_notify" and body.get(
                    "confID", "") == self.conf_id:
                # self.action_resource_lock.acquire()
                self.received_call_notify_num_list.append(kwargs["user_num"])
                # self.action_resource_lock.release()
                if kwargs["user_num"] != self.chairman_phone_num:
                    url = Constant.CONFS_URL + "/" + self.conf_id + "/callme"
                    basic_token = None
                    if "basicToken" in kwargs:
                        basic_token = kwargs["basicToken"]
                    headers = {'authorization': basic_token,
                               "Content-Type": "application/json; charset=utf-8"}
                    execute_http_client = HttpClient(url)
                    r = execute_http_client.request(method="POST", url=url,
                                                    name="/members/mss", catch_response=False,
                                                    headers=headers)
                    return r

            elif notify_name == "mx.conf.add_member_notify" and body.get(
                    "confID", "") == self.conf_id:
                notify_userID = body.get("userID", "")
                notify_conferMemberID = body.get("conferMemberID", "")
                # self.action_resource_lock.acquire()
                self.conf_mid_map.update({str(notify_userID): notify_conferMemberID})
                # self.action_resource_lock.release()
                self._logger.debug("Receive the add_mem notification, update the mid_map in the conf object.")

    def _init_mss(self):
        self._logger.info("execute mss_member")
        url = Constant.CONFS_URL + "/" + self.conf_id + "/members/mss"
        # url = Constant.CONFS_URL + "/" + self.conf_id + "/mss"
        method = 'POST'
        for in_conf_mem_phone_num in self.in_conf_mem_phone_num_list:
            # 这里需不需要资源锁？
            self.user_pool.cache_lock.acquire()
            conf_mem_obj = self.user_pool.user_phone_num_obj_dict[in_conf_mem_phone_num]
            self.user_pool.cache_lock.release()
            mss_data = self.random_mss_data(conf_mem_obj.user_info_dict["userID"])
            data = {
                "v": conf_mem_obj.conf_mss_v,
                "mss": mss_data
            }
            conf_mem_obj.conf_mss_v += 1
            data = json.dumps(data)
            headers = {'authorization': conf_mem_obj.user_info_dict["basicToken"],
                       "Content-Type": "application/json; charset=utf-8"}
            execute_http_client = HttpClient(url)
            r = execute_http_client.request(method=method, url=url, name="/members/mss",
                                            catch_response=False, headers=headers,
                                            data=data)
            # return r

    def random_mss_data(self, userID):
        mss_data = []
        copy_mid_map = copy.deepcopy(self.conf_mid_map)
        self._logger.debug(self.conf_mid_map)
        self._logger.debug(userID)
        conf_mem_num = len(copy_mid_map)
        if conf_mem_num > 6:
            select_num = 5
        else:
            select_num = conf_mem_num-1
        del copy_mid_map[str(userID)]
        choice_id_list = random.sample(copy_mid_map, select_num)
        for user_id in choice_id_list[:-1]:
            mss_data.append({"selected": int(copy_mid_map[user_id]),
                             "label": 2,  # label对于虚拟用户无意义，携带同样的
                             "level": 1})
        mss_data.append({"selected": int(copy_mid_map[choice_id_list[select_num-1]]),
                         "label": 2,  # label对于虚拟用户无意义，携带同样的
                         "level": 4})
        return mss_data

    def get_chair_mid(self):
        r = self.query_confs3()
        #user_mid = {}
        if r.status_code == 200:
            chair_mid = json.loads(r.text)["ginfo"]["chair"]
            user_mid = {str(self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num].user_info_dict["userID"]):chair_mid}
            self._logger.debug("detail:" + str(user_mid))
            return True, user_mid
        else:
            return False, {}

    def query_confs3(self):
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        URL = Constant.HOST + "/cxf/confs3/" + self.conf_id + "?param=DETAIL"
        r = requests.get(URL, headers=headers)
        self._logger.debug("detail:" + r.text)
        return r
