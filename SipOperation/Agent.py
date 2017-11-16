#!/usr/bin/env python
"""
Receive command and execute.After execute cmd finish,reply a message to commander.
This agent should be run on a linux machine that runs sipp or some other performance test tools.

"""
import amqplib.client_0_8 as amqp
from Logger import Logger
import threading
from SipMqConstants import SipMqConstants



def default_callback(msg):
    Logger.debug('default callback')
signal = threading.Event()
lock=threading.Lock()
class Agent:
    def __init__(self, host, username, pwd, exchange_name=SipMqConstants.MQ_AGENT_EXCHANGE, exchange_type='fanout',receive_callback=default_callback):
        self.conn = amqp.Connection(host=host, userid=username, password=pwd)
        self.exName = exchange_name
        self.ch = self.conn.channel()
        self.ch.access_request('/data', active=True, write=True)
        # self.ch.exchange_declare(self.exName, exType, auto_delete=True)
        self.ch.exchange_declare('cmder', 'fanout', auto_delete=False)
        self.ch.exchange_declare('agent', 'fanout', auto_delete=False)
        # self.ch.queue_declare(queue='agent_queue', durable=False, exclusive=False, auto_delete=True)
        # self.ch.queue_declare(queue='cmder_queue', durable=False, exclusive=False, auto_delete=True)
        # self.ch.queue_bind('agent_queue', 'agent')
        # self.ch.queue_bind('cmder_queue', 'cmder')
        self.result = self.ch.queue_declare(exclusive=True)
        self.ch.queue_bind(self.result[0], exchange_name)
        self.receive_callback=receive_callback

    def callback(self,msg):
        lock.acquire()
        Logger.debug('recv msg:'+str(msg.body))
        # msg.channel.basic_ack(msg.delivery_tag) noack to improve efficiency
        result=self.receive_callback(msg)
        if msg.body == 'quit':
            msg.channel.basic_cancel(msg.consumer_tag)
        lock.release()
    def start_receive(self):
        self.ch.basic_consume(self.result[0], no_ack=True,callback=self.callback)#no ack
        #
        # Loop as long as the channel has callbacks registered
        #
        while self.ch.callbacks:
            self.ch.wait()

    def sendBackMsg(self, msg):
        lock.acquire()
        message = amqp.Message(msg, content_type='text/plain', application_headers={'foo': 7, 'bar': 'baz'})
        self.ch.basic_publish(message, 'cmder')
        Logger.debug('sending reply msg: msg is '+msg)
        lock.release()
    def get_msg_id(self,msg):
        for key, val in msg.properties.items():
            if key == 'message_id':
                return str(val)
if __name__ == '__main__':
    agt = Agent('localhost', 'huwei', 'huwei')
    agt.start_receive()
    pass
