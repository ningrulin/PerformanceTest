# coding:utf-8
import logging
import copy
import threading
from collections import deque
"todo 深拷贝浅拷贝 复制"


class UserPoolCache(object):
    def __init__(self, user_set, p_stop_signal, preset_state, log_name="MXTest"):
        self._logger = logging.getLogger(log_name)

        self.cache_lock = threading.Lock()
        self.preset_state = preset_state
        self.p_stop_signal = p_stop_signal

        self.offline_user_phone_num_list = deque([])
        self.online_user_phone_num_list = deque([])

        self.user_phone_num_list = deque([])
        self.user_phone_num_obj_dict = {}

        self.group_mem_phone_num_list = deque([])
        self.group_id_list = deque([])
        self.group_id_obj_dict = {}

        self.conf_mem_phone_num_list = deque([])

        self.in_conf_mem_phone_num_list = deque([])
        self.out_conf_mem_phone_num_list = deque([])

        self.conf_chair_phone_num_list = deque([])
        self.conf_all_mem_phone_num_list = deque([])

        self.conf_id_list = deque([])
        self.conf_id_obj_dict = {}

        for user_obj in user_set:
            self.user_phone_num_obj_dict[user_obj.user_info_dict["userPhoneNum"]] = user_obj
            self.user_phone_num_list.append(user_obj.user_info_dict["userPhoneNum"])

        if preset_state == "offline_idle":
            self.offline_user_phone_num_list = copy.deepcopy(self.user_phone_num_list)

    def clear_cache(self):
        pass
