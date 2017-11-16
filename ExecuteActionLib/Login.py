# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
import logging
import time
import json
import base64
import traceback
from public.ConstantSet import Constant
from public.HttpClient import HttpClient
from public.websocket_clients import WebSocketClient
import hashlib


class LoginAction(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.executor_phone_num = None
        self.properly_executed = False
        self._logger = logging.getLogger(log_name)
        self.with_sip_register = False
        self._logger_ar = logging.getLogger("AllResult")

    def _execute_action(self):
        try:
            # 出现异常或者失败的情况是否终止当前任务的标志

            if "with_sip_register" in self.case_info_dict:
                self.with_sip_register = self.case_info_dict["with_sip_register"]

            self.user_pool.cache_lock.acquire()
            self.executor_phone_num = self.user_pool.offline_user_phone_num_list.pop()
            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]
            self.user_pool.cache_lock.release()

            self._logger.debug("start v3login:")
            http_result = self._execute_http_request()
            if http_result:
                self.user_pool.cache_lock.acquire()
                self.user_pool.online_user_phone_num_list.appendleft(self.executor_phone_num)
                self.user_pool.cache_lock.release()
                if self.with_sip_register is True:
                    pass
                    # TODO: make sip register. now we dont have this scenario.
                    # sip_register=SipRegisterMap.get_instance().get_sip_register(uuid.uuid1())
                    # sip_register.register_users_with_same_config()
                self._logger.info("Login success!")
                self.properly_executed = True
                self._logger_ar.debug("Login success!")
                return True
            else:
                self._logger.info("Login Fail!")
                self._logger_ar.debug("Login Fail!")
                return False

        except:
            self._logger.warning("Return False because of except.")
            self._logger_ar.debug("Login except!")
            self._logger.warning(traceback.format_exc())

        finally:

            sleep_after = 0
            if "sleep_after" in self.case_info_dict:
                sleep_after = self.case_info_dict["sleep_after"]

            if not self.properly_executed:
                self._clean_up_when_fail()

            time.sleep(sleep_after)

    def _execute_http_request(self):
        try:
            self.exe_success = False
            url = Constant.CAS_HOST + "/mhauth/login"
            method = "POST"
            data = {"username": self.executor_obj.user_info_dict["userPhoneNum"],
                    "type": "box",
                    "appkey": "10011801"}
            data = json.dumps(data)
            headers = {"Host": Constant.HOST_NAME,
                       "Content-Type": "text/html; charset=utf-8"}
            self._logger.debug("method: %s , url: %s , headers: %s , data: %s ." % (method, url, headers, data))
            execute_http_client = HttpClient(url)

            r = execute_http_client.request(method=method, url=url, name="/mhauth/login",
                                            catch_response=False, headers=headers, data=data)
            if r.status_code != 401:
                return False

            # get the dict mm = {"nonce": value1, "Digest realm": value2}
            c1 = r.headers
            dd = c1["Www-Authenticate"]
            kk = dd.split(',')
            mm = {}
            tt0 = kk[0].split('=')[0].strip()
            len1 = len(kk[0].split('=')[1].strip())
            mm.update({tt0: kk[0].split('=')[1].strip()[1:len1 - 1]})
            tt1 = kk[1].split('=')[0].strip()
            len2 = len(kk[1].split('=')[1].strip())
            mm.update({tt1: kk[1].split('=')[1].strip()[1:len2 - 1]})

            # start md5,get respone
            u_name = self.executor_obj.user_info_dict["userPhoneNum"]
            cc = mm['nonce']
            pwd = cc[int(u_name[4])] + cc[int(u_name[5])] + cc[int(u_name[6])] + cc[int(u_name[7])] \
                  + cc[int(u_name[8])] + cc[int(u_name[9])] + cc[int(u_name[10])] + cc[int(u_name[11])]
            ha1_str = u_name + ":" + mm['Digest realm'] + ":" + pwd
            has1 = hashlib.md5()
            has1.update(ha1_str)
            HA1 = has1.hexdigest()

            ha2_str = HA1 + mm['nonce']
            has2 = hashlib.md5()
            has2.update(ha2_str)
            HA2 = has2.hexdigest()

            # get service_token
            auth_str = "Digest username=" + "\"" + u_name + "\"" + ',' + 'realm=' + "\"" + mm[
                'Digest realm'] + "\"" + "," + \
                       "nonce=" + "\"" + mm['nonce'] + "\"" + ',' + 'response=' + "\"" + HA2 + "\""
            headers = {"Host": Constant.HOST_NAME,
                       "authorization": auth_str,
                       "Content-Type": "text/html; charset=utf-8"}
            execute_http_client = HttpClient(url)
            r = execute_http_client.request(method=method, url=url, name="/mhauth/login",
                                            catch_response=False, headers=headers)
            if r.status_code != 200:
                return False

            print r.text

            # get basetoken
            service_token = json.loads(r.text)["token"]
            time_stamp = str(int(round(time.time() * 1000)))
            base_token = 'Basic ' + base64.b64encode(service_token + ":" + time_stamp + ":" + "v1")

            # create ws
            self.executor_obj.mod_user_info_dict({"basicToken": base_token})
            user_ws_client = WebSocketClient(self.executor_obj.user_info_dict["userPhoneNum"],
                                             self.executor_obj.user_info_dict["basicToken"], self.user_pool,
                                             self.p_stop_signal)
            self.executor_obj.set_ws_client(user_ws_client)
            self.executor_obj.ws_client.start()
            self.executor_obj.mod_user_info_dict({"refresh_token": json.loads(r.text)["refresh_token"]})
            self._logger.info("execute login")
            return True
        except:
            self._logger.error("Return False because of except.")
            self._logger.error(traceback.format_exc())
            return False

    def _clean_up_when_fail(self):
        """release user source when fail."""
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
            if self.executor_phone_num not in self.user_pool.offline_user_phone_num_list:
                self.user_pool.offline_user_phone_num_list.appendleft(self.executor_phone_num)
                if self.executor_phone_num in self.user_pool.online_user_phone_num_list:
                    self.user_pool.online_user_phone_num_list.delete(self.executor_phone_num)
            self.user_pool.cache_lock.release()
