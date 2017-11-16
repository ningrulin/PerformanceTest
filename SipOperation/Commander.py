#!/usr/bin/env python
"""
Send a command to a agent through mq.

"""
from optparse import OptionParser
import threading
import amqplib.client_0_8 as amqp
from Logger import Logger
from SipMqConstants import SipMqConstants
import time
def default_user_callback(msg):
    print 'in default callback'
    pass


def my_callback():
    print 'in my callback'
    signal.set()

signal = threading.Event()
lock=threading.Lock()

cmder_lock=threading.Lock()
class CommanderMap():
    instance = None
    mutex = threading.Lock()

    def __init__(self):
        self.commander_map={}
        pass

    @staticmethod
    def get_instance():
        if (CommanderMap.instance == None):
            CommanderMap.mutex.acquire()
            if (CommanderMap.instance == None):
                Logger.debug('commander map not init, initing..')
                CommanderMap.instance = CommanderMap()
            else:
                Logger.debug('commander map inited')
            CommanderMap.mutex.release()
        else:
            Logger.debug('commander map is init, return..')

        return CommanderMap.instance
    def get_commander(self,id):
        cmder_lock.acquire()
        result= Commander.get_commander()
        cmder_lock.release()
        return result
    def release_commander(self,id):
        Commander.get_commander().stop_receive()
class Commander:
    instance=None
    @classmethod
    def get_commander(cls):#caution: use this method with locks.
        if Commander.instance is None:
            Commander.instance=Commander()
            return Commander.instance
        else:
            return Commander.instance
    def __init__(self, host=SipMqConstants.MQ_REMOTE_SERVER, username=SipMqConstants.MQ_USER, pwd=SipMqConstants.MQ_PASSWORD, exchange_name=SipMqConstants.MQ_CMDER_EXCHANGE, agent_queue=SipMqConstants.MQ_AGENT_QUEUE_NAME, agent_exchange=SipMqConstants.MQ_AGENT_EXCHANGE, exchange_type=SipMqConstants.MQ_CMDER_EXCHANGE_TYPE):
        Logger.debug('commander is initing...'+str(self))
        self.is_receiving=False
        self.host=host
        self.username=username
        self.pwd=pwd
        self.conn = amqp.Connection(host=host, userid=username, password=pwd)
        self.exName = exchange_name
        self.ch = self.conn.channel()
        self.ch.access_request('/data', active=True, write=True)
        # self.queue_name='cmder_queue_'+str(time.time())
        self.queue_name = 'cmder_queue'
        self.ch.queue_declare(queue=self.queue_name, exclusive=False)
        self.ch.queue_bind(self.queue_name,exchange_name)
        self.consumer_tag=None
        self.user_callbacks={}
        self.receving_lock=threading.Lock()
        t1 = threading.Thread(target=self.start_receive)
        t1.start()
    def callback(self, msg):
        Logger.debug('cmder '+str(self)+' recv a msg '+msg.body)
        lock.acquire()
        # msg.channel.basic_ack(msg.delivery_tag)
        if msg.body == 'quit':
            msg.channel.basic_cancel(msg.consumer_tag)
        lock.release()
        # Logger.debug('in Commander receive msg callback,msg is '+msg.body)
        msgdic = eval(msg.body)
        id=msgdic['reply_id']
        if self.user_callbacks.has_key(id):
            Logger.debug('receve msg for id '+id)
            self.user_callbacks[id](msg)
            #new thread to handle callback
            t1 = threading.Thread(target= self.user_callbacks[id],args=(msg,))
            t1.start()

        else:
            Logger.error('receve msg for unknow id ' + str(id))
        # if self.user_callback is not None:
        #     self.user_callback(msg)
        #
        # Cancel this callback
        #

    def start_receive(self):
        self.receving_lock.acquire()
        if self.is_receiving is True:
            return
        Logger.debug('cmder start receive reply msg')
        self.consumer_tag=self.ch.basic_consume(self.queue_name, no_ack=True,callback=self.callback)
        self.is_receiving=True
        self.receving_lock.release()
        #
        # Loop as long as the channel has callbacks registered
        #
        while self.ch.callbacks:
            self.ch.wait()
    def stop_receive(self):
        print '0'
        if self.is_receiving is False:
            self.receving_lock.release()
            return
        #self.ch.basic_cancel(self.consumer_tag)
        #self.ch.close()
        print '1'
        print 'tag is '+str(self.consumer_tag)
        # self.ch.basic_cancel(self.consumer_tag,nowait=True)
        print '2'
        self.ch.close()
        print '3'
        self.conn.close()
        print '4'
        self.is_receiving=False
        print '5'

    def send_cmd(self, msg,id, userCallback=default_user_callback):
        lock.acquire()
        Logger.debug('in cmder, sending msg ...' + msg)
        message = amqp.Message(msg, content_type='text/plain', application_headers={'foo': 7, 'bar': 'baz'})
        self.ch.basic_publish(message, 'agent')
        # self.user_callback = userCallback
        self.user_callbacks[id]=userCallback
        lock.release()
if __name__ == '__main__':
    cmder = Commander('localhost', 'huwei', 'huwei')
    t1 = threading.Thread(target=cmder.start_receive)
    t1.setDaemon(True)
    t1.start()
    # cmder.sendCmd("date",myCallback)
    cmder.send_cmd("sipp -i 192.168.220.129 -p 5083 -inf /home/alhu/sipp/sipxml/users_reg.csv -sf /home/alhu/sipp/sipxml/uac_register.xml 192.168.5.201:6650 -r 1 -rp 1000 -aa",'1')

    signal.wait()
    print 'this line'
    cmder.stop_receive()

