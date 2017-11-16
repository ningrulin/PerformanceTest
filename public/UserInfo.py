# coding:UTF-8
import logging


class User(object):
    # 这些参数是不是可以使用动态参数？ * **
    def __init__(self, user_info_dict, ws_client, log_name="MXTest"):
        # runEnvir:test|develop|offical
        # deviceType:pc|tv|ios|android
        self._logger = logging.getLogger(log_name)
        self.ws_client = ws_client
        self.attach_group_id = None
        self.in_group = False
        self.attach_conf_id = None

        # todo not hand
        self.is_aff = False
        self.in_conf = False
        self.conf_mss_v = 0
        self.user_info_dict = {
            "userID": None,
            "name": None,
            "commName": None,
            "photoPath": None,
            "sex": None,
            "sign": None,
            "stateOrProvince": None,
            "organization": None,
            "orgUnit": None,
            "mail": None,
            "owner": None,
            "type": None,
            "role": None,
            "mobile": None
        }
        self.user_info_dict.update(user_info_dict)

    def mod_user_info_dict(self, user_info_dict):
        if isinstance(user_info_dict, dict):
            self.user_info_dict.update(user_info_dict)
            self._logger.info(str(self.user_info_dict))
        else:
            self._logger.error("Parameter is not a dictionary type!")

    def set_ws_client(self, ws_client):
        self.ws_client = ws_client
