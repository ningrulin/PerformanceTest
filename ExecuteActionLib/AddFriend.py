# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
import logging
import time
import json
import traceback
from public.ConstantSet import Constant
from public.HttpClient import HttpClient


class AddFriendAction(ExecuteAction):
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
            self.all_friends_phone_num = self.user_pool.online_user_phone_num_list
            """这一块用作特殊添加好友使用，逻辑与其他的Action不同，不用于测试使用，只用来生成前置条件"""

            for phone_num in self.all_friends_phone_num:
                self.executor_phone_num = phone_num
                self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]
                for phone_num_added in self.all_friends_phone_num:
                    # self.added_friend_phone_num = phone_num_added
                    self.added_friend_obj = self.user_pool.user_phone_num_obj_dict[phone_num_added]
                    self._execute_http_request()
                    # http_response = self._execute_http_request()

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
                self._logger.info("AddFriend success!")
                self._logger.info("Sleep %s s after action!" % sleep_after)
                time.sleep(sleep_after)
                return True
            else:
                self.user_pool.cache_lock.acquire()
                self.user_pool.online_user_phone_num_list.appendleft(self.executor_phone_num)
                self.user_pool.cache_lock.release()
                self._logger.info("AddFriend Fail!")
                self._logger.info("Sleep %s s after action!" % sleep_after)
                if abnormal_interrupt:
                    self.p_stop_signal.set()
                    # False，设置终止整个进程信号
                time.sleep(sleep_after)
                return False
        except:
            if self.user_pool.cache_lock.locked():
                self.user_pool.cache_lock.release()
            self._logger.warning("AddFriend Return False because of except.")
            # todo 需不需要放回用户列表中取
            self._logger.warning(traceback.format_exc())
            # 出现异常，设置终止整个进程信号
            abnormal_interrupt = True
            if "abnormal_interrupt" in self.case_info_dict:
                abnormal_interrupt = self.case_info_dict["abnormal_interrupt"]
            if abnormal_interrupt:
                self.p_stop_signal.set()
                # False，设置终止整个进程信号
            return False
        finally:
            """添加好友操作，暂时不涉及到服务器测试用例中，先暂时不处理finally这一块."""
            pass

    def _execute_http_request(self):
        self._logger.info("execute AddFriend")
        url = Constant.ADD_FRIEND_URL
        method = 'POST'
        data = json.dumps({
                "id": str(self.executor_obj.user_info_dict["userID"]),
                "contactid": str(self.added_friend_obj.user_info_dict["userID"]),
                "type": "TERMINAL",
                "nickname": self.executor_obj.user_info_dict["commName"],
                "contactnick": str(self.added_friend_obj.user_info_dict["commName"]),
                "comment": "hello.",
                "usertype": "TERMINAL",
                "addtype": ""})

        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name="/contact/add/friend",
                                        data=data, catch_response=False, headers=headers)
        self._logger.info(r.text)
        self._logger.info(url)
        self._logger.info(data)
        return r
