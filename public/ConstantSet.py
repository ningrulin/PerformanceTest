# coding:utf-8


class Constant(object):
    # 所有的全局常量定义在这里
    # 性能测试环境IP配置
   # CAS_HOST = "http://192.168.5.61"
   # HOST = "http://192.168.5.61"
   # HOST_NAME = "192.168.5.61"
   # PUSH_HOST = "ws://192.168.5.61:80"
   # SIP_HOST = "192.168.5.63:6650"
   
    CAS_HOST = "http://192.168.1.101"
    HOST = "http://192.168.1.101"
    HOST_NAME = "192.168.1.101"
    PUSH_HOST = "ws://192.168.1.101:80"
    SIP_HOST = "192.168.1.103:6650"

    WS_URL = PUSH_HOST+"/push/subscribe"

    LOGIN_URL = CAS_HOST + "/cas/v1/tickets"
    LOGOUT_URL = CAS_HOST + "/cas/v1/tickets"

    GROUP_ENABLE_SHARE_URL = HOST + "/group/id/enable/share"
    CREATE_GROUP_URL = HOST + "/group/create/group"
    GET_GROUP_LIST_URL = HOST + "/user/list/groups"
    GET_CONTACT_LIST_URL = HOST + "/contact/list/contacts"
    GET_USER_INFO_URL = HOST + "/cxf/security/persons"
    MOD_USER_INFO_URL = HOST + "/contact/user/mod"
    JOIN_GROUP_BY_ID_URL = HOST + "/group/id/join"
    ADD_FRIEND_URL = HOST + "/contact/add/friend"

    CONFS_URL = HOST + "/cxf/confs3"
