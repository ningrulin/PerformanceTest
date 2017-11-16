#!/usr/bin/env python
from SipUtil import SipUtil
import os
class SipMqConstants():
    MQ_LOCAL_SERVER= SipUtil.get_local_ip()
    MQ_REMOTE_SERVER=SipUtil.get_local_ip()
    MQ_USER= 'guest'
    MQ_PASSWORD= 'guest'
    MQ_CMDER_EXCHANGE='cmder'
    MQ_AGENT_QUEUE_NAME='agent_queue'
    MQ_CMDER_EXCHANGE_TYPE='fanout'
    MQ_AGENT_EXCHANGE='agent'
    SIP_SERVER='192.168.1.103:6650'
    SIP_REG_SERVER = '192.168.1.102:6650'
    SIP_MEDIA_SERVER = '192.168.1.103:6650'
    SIP_PORT='6650'
    SIP_PASSWORD='6666'
    SIP_XML_PATH = os.path.dirname(__file__) + '/sipxml/'
    SIP_AUDIO_PCAP_FILE='''pcap/3sec_g711a.pcap'''
    SIP_VIDEO_PCAP_FILE='''pcap/v.pcap'''
