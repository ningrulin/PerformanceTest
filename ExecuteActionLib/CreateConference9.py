# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
from SipOperation.SipCall import *
from SipOperation.SipRegister import *
from public.ConstantSet import Constant
from public.HttpClient import HttpClient
from public.ConferenceInfo import ConferenceInfo
from requests.exceptions import ConnectionError
import logging
import threading
import time
import copy
import json
import requests
import traceback
import random
import uuid


class CreateConf9Action(ExecuteAction):
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
        self.received_inconf_info = []
        self.flage = False
        self.received_member_num_list = []
        self.members_num_list = []
        self.properly_executed = False
        self.is_init_mss = False
        self._logger = logging.getLogger(log_name)
        self.in_conf_num = 0

    def _execute_action(self):
        try:
            reg_callee_caps = 10
            if "reg_callee_caps" in self.case_info_dict:
                reg_callee_caps = self.case_info_dict["reg_callee_caps"]

            self.only_self = False
            if "only_self" in self.case_info_dict:
                self.only_self = self.case_info_dict["only_self"]

            if "is_init_mss" in self.case_info_dict:
                self.is_init_mss = self.case_info_dict["is_init_mss"]

            if "in_conf_num" in self.case_info_dict:
                self.in_conf_num = self.case_info_dict["in_conf_num"]

            self.user_pool.cache_lock.acquire()
            self.conf_group_id = self.user_pool.group_id_list.pop()
            self.user_pool.cache_lock.release()

            self._logger.debug("this group_id is: " + str(self.conf_group_id))
            self._logger.debug("self.user_pool.group_id_list: " + str(self.user_pool.group_id_list))

            self.group_obj = self.user_pool.group_id_obj_dict[self.conf_group_id]
            self.chairman_phone_num = self.group_obj.group_owner_phone_num
            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num]

            self.conf_mem_phone_num_list = copy.deepcopy(self.group_obj.group_mem_phone_num_list)
            self.conf_all_mem_phone_num_list = copy.deepcopy(self.conf_mem_phone_num_list)
            self.conf_all_mem_phone_num_list.append(self.chairman_phone_num)

            if self.only_self:
                self.in_conf_mem_phone_num_list = []
                self.out_conf_mem_phone_num_list = self.conf_mem_phone_num_list
            else:
                """if self.in_conf_num != 0:
                    self.in_conf_mem_phone_num_list = random.sample(self.conf_mem_phone_num_list, self.in_conf_num)
                    self.out_conf_mem_phone_num_list = list(set(self.conf_mem_phone_num_list)^ set(self.in_conf_mem_phone_num_list))
                else:"""
                self.in_conf_mem_phone_num_list = self.conf_mem_phone_num_list
                self.out_conf_mem_phone_num_list = []

            self.all_in_conf_mem_phone_number_list = copy.deepcopy(self.in_conf_mem_phone_num_list)
            self.all_in_conf_mem_phone_number_list.append(self.chairman_phone_num)


            # 主席的sip_number
            """conf_chairman_sip_number = str(
                self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num].user_info_dict["userID"]) + "00" """
            #临时集群环境使用的sip号：
            conf_chairman_sip_number = str(
                int(str(self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num].user_info_dict["userPhoneNum"])[1:12])
                - 11525100001 + 10010000019) + "00"
            self._logger.debug("aqf print chair_phone_num" + str(self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num].user_info_dict["userPhoneNum"]))
            self._logger.debug("aqf print sipnumber" + str(conf_chairman_sip_number))
            # 所有会议成员的sip_number 不包括主席
            for in_conf_mem_phone_num in self.in_conf_mem_phone_num_list:
                """conf_mem_sip_number = str(
                    self.user_pool.user_phone_num_obj_dict[in_conf_mem_phone_num].user_info_dict["userID"]) + "00" """
                # 临时集群环境使用的sip号：
                conf_mem_sip_number = str(
                int(str(self.user_pool.user_phone_num_obj_dict[in_conf_mem_phone_num].user_info_dict["userPhoneNum"])[1:12])
                - 11525100001 + 10010000019) + "00"
                self._logger.debug("aqf print sipnumber" + str(conf_mem_sip_number))
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
                # "userID": self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num].user_info_dict["userID"],
                "uid": self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num].user_info_dict["userID"],
                "name": self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num].user_info_dict["commName"]}
            self.all_in_conf_mem_info_dict.append(chairman_info_dict)

            in_conf_mem_num = len(self.in_conf_mem_phone_num_list)
            all_in_conf_mem_num = in_conf_mem_num + 1
            sip_reg_callee_timeout = (all_in_conf_mem_num) // reg_callee_caps + 3

            uuid_now = uuid.uuid1()
            # sip 注册，对应会议群中所有成员
            """sip_reg = SipRegisterMap.get_instance().get_sip_register(
                    str(self.conf_group_id)+"_"+str(uuid_now), SipMqConstants.SIP_SERVER)"""
            sip_reg = SipRegisterMap.get_instance().get_sip_register(
                str(self.conf_group_id) + "_" + str(uuid_now), SipMqConstants.SIP_REG_SERVER)


            # 主叫列表
            caller_sip_number_list = []
            caller_sip_number_list.append(conf_chairman_sip_number)

            """sip_reg_flag, caller_port, callee_port = \
                sip_reg.register_users_with_same_config(caller_sip_number_list,
                                                        self.in_conf_mem_sip_number_list,
                                                        SipMqConstants.SIP_SERVER,
                                                        SipMqConstants.SIP_PASSWORD,
                                                        reg_callee_caps,
                                                        sip_reg_callee_timeout)"""
            sip_reg_flag, caller_port, callee_port = \
                sip_reg.register_users_with_same_config(caller_sip_number_list,
                                                        self.in_conf_mem_sip_number_list,
                                                        SipMqConstants.SIP_REG_SERVER,
                                                        SipMqConstants.SIP_PASSWORD,
                                                        reg_callee_caps,
                                                        sip_reg_callee_timeout)

            if not sip_reg_flag:
                self._logger.error("sip registration failed!")
                return False

            self._logger.debug("he calling port and the called port are: %s,%s" % (str(caller_port), str(callee_port)))

            # 添加handler 监听是否收到call notify
            for conf_mem_phone_num in self.all_in_conf_mem_phone_number_list:
                conf_mem_obj = self.user_pool.user_phone_num_obj_dict[conf_mem_phone_num]
                conf_mem_obj.ws_client.add_handler(self._analyze_notify)


            self._logger.debug("aqf print start time: " + time.strftime('%H%M%S', time.localtime(time.time())))

            r = self._execute_http_request()
            if r.status_code != 200:
                self._logger.warning(str(r.text))
                self._logger.error("Create confs fail!")
                return False

            conf_id = json.loads(r.text)["id"]
            self.conf_id = conf_id
            self._logger.info("Create confs success!"+str(self.conf_id))

            # 先拉起被叫
            # sip 被叫流程
            # 如果是一个人的会议就不需要被叫流程了
            sipcall = SipCallMap.get_instance().get_sip_call(str(self.conf_group_id)+"_"+str(uuid_now))

            if not self.only_self:
                callee_number = len(self.in_conf_mem_sip_number_list)
                self._logger.debug("callee_number:" + str(callee_number))
                if not sipcall.get_callee_ready(str(conf_id), callee_number, SipMqConstants.SIP_MEDIA_SERVER, reg_callee_caps,
                                                callee_port, 36000, sip_reg_callee_timeout):
                    self._logger.error("Sip called failed to create.")
                    return False

                self._logger.info("Sip called success!")
                time.sleep(5)

            # 主叫
            if not sipcall.make_call(caller_sip_number_list, str(conf_id),
                                     SipMqConstants.SIP_MEDIA_SERVER, SipMqConstants.SIP_PASSWORD,
                                     caller_port, 1000, 10, 15):
                self._logger.error("Sip caller failed!")
                return False
            self._logger.info("Sip caller is successful!")

            if not self.only_self:
                time_out = 1000
                while time_out:
                    self.action_resource_lock.acquire()
                    if len(self.received_call_notify_num_list) == all_in_conf_mem_num and len(self.received_inconf_info) == all_in_conf_mem_num:
                        self.action_resource_lock.release()
                        print "break"
                        break
                    self.action_resource_lock.release()
                    time.sleep(1)
                    time_out -= 1

                self._logger.debug("aqf print end time: " + time.strftime('%H:%M:%S', time.localtime(time.time())))

                self._logger.debug("aqf: print self.received_call_notify_num_list" + str(self.received_call_notify_num_list))
                self._logger.debug("aqf: print all_in_conf_mem_num" + str(all_in_conf_mem_num))
                self._logger.debug("aqf: print self.chairman_phone_num" + str(self.chairman_phone_num))
                self._logger.debug("aqf: print main self.received_inconf_info" + str(self.received_inconf_info))



                if len(self.received_call_notify_num_list) < all_in_conf_mem_num :
                    self._logger.error("Expected to receive call_notify Quantity:" + str(all_in_conf_mem_num) +
                                       " Actually received call_notify Quantity:" +
                                       str(len(self.received_call_notify_num_list)) +
                                       " self.received_call_notify_num_list" +
                                       str(self.received_call_notify_num_list) + " Conference ID: " + str(self.conf_id))

                    return False

                if len(self.received_inconf_info) == all_in_conf_mem_num:
                    self.flage =True

                self._logger.debug("Expected to receive call_notify Quantity:" + str(all_in_conf_mem_num) +
                                   " Actually received call_notify Quantity:" + str(len(self.received_call_notify_num_list)) +
                                   " self.received_call_notify_num_list" +
                                   str(self.received_call_notify_num_list) + " Conference ID: " + str(self.conf_id))
            else :
                self.flage = True

            mid_flag, mid = self.get_conf_mid(self.conf_id, self.executor_obj.user_info_dict["basicToken"])
            #mid_flag, mid = self._get_conf_mid_list(self.conf_id, self.executor_obj.user_info_dict["basicToken"])

            if mid_flag:
                self.conf_mid_map.update(mid)
                self._logger.debug("Get user mid success!")
            else:
                self._logger.error("Get user mid fail!")
                self.flage = False

            # todo 这里暂时使用sip_reg_callee_timeout 来代替Sip 入会时间.
            time.sleep(sip_reg_callee_timeout)

            # 去掉handler
            for conf_mem_phone_num in self.all_in_conf_mem_phone_number_list:
                conf_mem_obj = self.user_pool.user_phone_num_obj_dict[conf_mem_phone_num]
                conf_mem_obj.ws_client.sub_handler(self._analyze_notify)

            if self.is_init_mss:
                self._init_mss()  # 初始化选流，需不需要判断结果？暂时不做判断，只做模拟

            self.user_pool.cache_lock.acquire()
            self.group_obj.is_in_conf = True
            self.group_obj.conf_id = conf_id
            conf_obj = ConferenceInfo(self.conf_group_id, conf_id, self.chairman_phone_num,
                                      self.conf_mem_phone_num_list, self.out_conf_mem_phone_num_list,
                                      self.in_conf_mem_phone_num_list, self.conf_mid_map)
            self._logger.debug("CreateConf in_conf_mem_num_list: " + str(conf_obj.in_conf_mem_num_list))

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

            self.user_pool.group_id_list.appendleft(self.conf_group_id)
            self.user_pool.cache_lock.release()
            if self.flage:
                self._logger.debug("The conference was created successfully!")
            else:
                self._logger.debug("The conference was created failed!")
            self.properly_executed = True

        except:
            self._logger.error("Return False because of except.")
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
        """
        当测试执行失败后，执行该操作
        :return:
        """
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
        self._logger.info("execute create_conference")
        url = Constant.CONFS_URL
        # url = "http://test.meetsoon.net/cxf/confs2"
        method = 'POST'
        # 使用把参数列表中的groupshareid

        self._logger.debug("self.all_in_conf_mem_info_dict" + str(self.all_in_conf_mem_info_dict))
        self._logger.debug("self.all_in_conf_mem_info_dict len:" + str(len(self.all_in_conf_mem_info_dict)))
        #self.all_in_conf_mem_info_dict

        data = {"gid": self.conf_group_id,
                "members": self.all_in_conf_mem_info_dict,
                "systemOpenGroup": "false",
                "onlyself": self.only_self
                }
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url,
                                        name="create_conference",
                                        catch_response=False, headers=headers,
                                        data=json.dumps(data))
        return r

    def _analyze_notify(self, **kwargs):
        if "message" in kwargs:
            json_data = json.loads(kwargs["message"])
            event = json_data.get("event", {})
            event_name = event.get("name", "")
            self._logger.debug("aqf: print name:" + str(event.get("name", "")))
            self._logger.debug("aqf: print event_body:" + str(event.get("body", [])))

            if event_name == "mx.conf3.arrayNotify" :
                if "body" in event:
                    event_body = event.get("body", [])
                else:
                    event_body = event
                self._logger.debug("aqf: print event_body:" + str(event_body))

                if event.get("cid", "") == self.conf_id:
                    self._logger.debug("aqf: start do with mx.conf3.arrayNotify")
                    for sigle_event in event_body:
                        if sigle_event["name"] == "mx.conf3.member":
                            self._logger.debug("aqf: mx.conf3.member" + str(sigle_event.get("body", {})))
                            if sigle_event.get("body", {})["ol"] :
                                if kwargs["user_num"] not in self.received_inconf_info:
                                    event_uid = sigle_event.get("body", {})["uid"]
                                    event_mid = sigle_event.get("body", {})["mid"]
                                    self._logger.debug("aqf: print kwargs "+ str(kwargs["user_num"]))
                                    self.received_inconf_info.append(kwargs["user_num"])
                                    self.conf_mid_map.update({str(event_uid): event_mid})
                                    self._logger.debug("Receive the add_mem notification, update the mid_map in the conf object.")
                                    self._logger.debug("aqf: print self.received_inconf_info " + str(self.received_inconf_info))
                            else:
                                if kwargs["user_num"] in self.received_inconf_info:
                                    self.received_inconf_info.remove(kwargs["user_num"])

            elif event_name == "mx.conf3.invite" :
                if "body" in event:
                    event_body = event.get("body", {})
                else:
                    event_body = event
                if event_body.get("id", "") == self.conf_id:
                    self.received_call_notify_num_list.append(kwargs["user_num"])
                    if kwargs["user_num"] != self.chairman_phone_num :
                        url = Constant.CONFS_URL + "/" + self.conf_id + "/callme"
                        basic_token = None
                        if "basic_token" in kwargs:
                            basic_token = kwargs["basic_token"]
                        headers = {'authorization': basic_token,
                                   "Content-Type": "application/json; charset=utf-8"}
                        data = {"device": "ios"}
                        data = json.dumps(data)
                        execute_http_client = HttpClient(url)
                        r = execute_http_client.request(method="POST", url=url, name="/callme",
                                                        catch_response=False,
                                                        headers=headers, data = data)
                        return r

    def _init_mss(self):
        self._logger.info("execute mss_member")
        url = Constant.CONFS_URL + "/" + self.conf_id + "/members/mss"
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
            r = execute_http_client.request(method=method, url=url, name="/members/mss", catch_response=False,
                                            headers=headers, data=data)
            # return r

    def random_mss_data(self, user_id):
        mss_data = []
        copy_mid_map = copy.deepcopy(self.conf_mid_map)
        self._logger.debug(self.conf_mid_map)
        self._logger.debug(user_id)
        conf_mem_num = len(copy_mid_map)
        if conf_mem_num > 6:
            select_num = 5
        else:
            select_num = conf_mem_num-1
        del copy_mid_map[str(user_id)]
        choice_id_list = random.sample(copy_mid_map, select_num)
        for selected_user_id in choice_id_list[:-1]:
            mss_data.append({"selected": int(copy_mid_map[selected_user_id]),
                             "label": 2,  # label对于虚拟用户无意义，携带同样的
                             "level": 1})
        mss_data.append({"selected": int(copy_mid_map[choice_id_list[select_num-1]]),
                         "label": 2,  # label对于虚拟用户无意义，携带同样的
                         "level": 4})
        return mss_data

    def query_confs2(self, conf_id, basic_token):
        try:
            headers = {'authorization': basic_token,
                       "Content-Type": "application/json; charset=utf-8"}
            URL = Constant.HOST + "/cxf/confs2/" + conf_id
            r = requests.get(URL, headers=headers)
            r.close()
            if int(r.status_code) == 200:
                userIDMap = json.loads(r.text)["userIDMap"]
                return True, r.text
            elif int(r.status_code) == 404:
                return False, "no conf_id"
            else:
                return False, r.status_code
        except ConnectionError as e:
            print e
            return False, "ConnectionError"

    def get_conf_mid(self, conf_id, basic_token):
        q_flag, r_text = self.query_confs2(conf_id, basic_token)
        if q_flag:
            user_mid = json.loads(r_text)["userIDMap"]
            return True, user_mid
        else:
            return False, {}

    def _query_confs3(self, conf_id , basic_token):
        try:
            headers = {'authorization': basic_token,
                       "Content-Type": "application/json; charset=utf-8"}
            URL = Constant.CONFS_URL + "/" + str(conf_id) +"?param=DETAIL"
            r = requests.get(URL, headers=headers)
            r.close()
            self._logger.debug("aqf:r.r" + str(r.status_code))
            self._logger.debug("aqf:r.text" + str(r.text))
            if int(r.status_code) == 200:
                return True, r.text
            elif int(r.status_code) == 404:
                return False, "no conf_id"
            else:
                return False, r.status_code
        except ConnectionError as e:
            print e
            return False, "ConnectionError"

    def _get_conf_mid_list(self, conf_id , basic_token):
        q_flag, r_text = self._query_confs3(conf_id, basic_token)
        if q_flag:
            #user_mid = json.loads(r_text)["userIDMap"]
            return True, {}
        else:
            return False, {}
