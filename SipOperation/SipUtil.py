#!/usr/bin/env python
"""
utils about sip operation

"""
import commands,re,uuid
from Logger import Logger
class SipUtil(object):
    local_ip=None
    def __init__(self):
        pass
    '''
    get mq msg id.
    '''
    @classmethod
    def get_msg_id(cls,msg):
        for key, val in msg.properties.items():
            print ('%s: %s' % (key, str(val)))
            if key == 'message_id':
                return str(val)
    @classmethod
    def get_local_ip(cls):
        if SipUtil.local_ip is not None:
            return SipUtil.local_ip
        out = commands.getoutput('ifconfig')
        reg = re.compile("addr:(?:[0-9]{1,3}\.){3}[0-9]{1,3}")
        ips=reg.findall(out)
        for item in ips:
            ip=item.split(':')[1]
            #only count internal ip
            if ip.startswith('172') or ip.startswith('192'):
                Logger.debug('find local ip is '+str(ip))
                SipUtil.local_ip=ip
                return ip
        Logger.debug('unable to find a local ip!')
        return None

    @classmethod
    def get_local_port(cls):
        return "15088"
def loop():
    while True:
        print 'sss'
def sip_register(caller_list,callee_list,host,password,caps,reg_duration):
    from SipRegister import SipRegisterMap
    sip_register = SipRegisterMap.get_instance().get_sip_register('1')
    result,p1,p2=sip_register.register_users_with_same_config(sip_numbers_caller=caller_list,sip_numbers_callee=callee_list, host=host, password=password, caps=caps, reg_duration=reg_duration)
    Logger.debug("result is "+str(result))
    return result,p1,p2
if __name__ == '__main__':
#     out='''eth0      Link encap:Ethernet  HWaddr 00:0c:29:de:7d:a4
#           inet addr:192.168.5.87  Bcast:192.168.5.255  Mask:255.255.255.0
#           inet6 addr: fe80::20c:29ff:fede:7da4/64 Scope:Link
#           UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
#           RX packets:46264593 errors:0 dropped:0 overruns:0 frame:0
#           TX packets:40155934 errors:0 dropped:0 overruns:0 carrier:0
#           collisions:0 txqueuelen:1000
#           RX bytes:22342900060 (22.3 GB)  TX bytes:12759127825 (12.7 GB)
#
# lo        Link encap:Local Loopback
#           inet addr:127.0.0.1  Mask:255.0.0.0
#           inet6 addr: ::1/128 Scope:Host
#           UP LOOPBACK RUNNING  MTU:65536  Metric:1
#           RX packets:399 errors:0 dropped:0 overruns:0 frame:0
#           TX packets:399 errors:0 dropped:0 overruns:0 carrier:0
#           collisions:0 txqueuelen:0
#           RX bytes:42676 (42.6 KB)  TX bytes:42676 (42.6 KB)'''
    #print SipUtil.get_local_ip(out)
    # replace_pcap=r'''sed -r 's/play_pcap_audio=".*"/play_pcap_audio="/root/PerformanceTest/SipOperation/sipxml/v.pcap"/g' uac_caller.xml'''
    # print replace_pcap
    # s=replace_pcap.replace(r'/',r'\/')
    # print s
    import time
    import Utils as Utils
    nowtime_str = time.strftime('%Y%m%d_%H%M%S', time.localtime(time.time()))
    print nowtime_str
    #LINUX
    DebugLogPath = Utils.create_folder("TestResult/DebugLog/")
    ResultLogPath = Utils.create_folder("TestResult/HttpResult/")
    CountLogPath = Utils.create_folder("TestResult/CountResult/")
    #WINDOWS
    """DebugLogPath = Utils.create_folder("TestResult\\DebugLog\\")
    ResultLogPath = Utils.create_folder("TestResult\\HttpResult\\")"""
    debug_log_file = DebugLogPath + nowtime_str + "_Debug.log"
    result_log_file = ResultLogPath + nowtime_str + ".log"
    count_log_file = CountLogPath + nowtime_str + "_http_result.log"
    logger = Utils.create_debug_logger("MXTest", debug_log_file)
    logger_db = Utils.create_http_result_logger("Result", result_log_file)
    logger_cn = Utils.create_http_result_logger("Count", count_log_file)
    from SipMqConstants import SipMqConstants
    caller_list=['1001000010100']
    callee_list=['1001000009400','1001000009600','1001000009700','1001000010100','1001000009800','1001000010000','1001000009500','1001000009300','1001000009200']
    for i in range(0,10000):
        Logger.debug("loop: "+str(i))
        result,p1,p2=sip_register(caller_list,callee_list,SipMqConstants.SIP_SERVER,SipMqConstants.SIP_PASSWORD,10,5)
        if result is False:
            Logger.debug("REGISTER FAILED!!!!!!!!!")
            break
    print 'finish'


