#!/usr/bin/env python
"""
Serve as a mq server.

"""
import amqplib.client_0_8 as amqp
from SipMqConstants import SipMqConstants
class MQServer(object):
    def __init__(self,agent_exchange_name='agent',agent_queue_name='agent_queue',cmder_exchange_name='cmder',cmder_queueu_name='cmder_queue',mq_user='huwei',mq_password='huwei'):
        self.conn = amqp.Connection(host='localhost', userid=mq_user, password=mq_password)
        self.ch = self.conn.channel()
        self.ch.exchange_declare('cmder', 'fanout', auto_delete=True)
        self.ch.exchange_declare('agent', 'fanout', auto_delete=True)
        self.ch.queue_declare(queue='agent_queue', durable=True, exclusive=False, auto_delete=False)
        self.ch.queue_declare(queue='cmder_queue', durable=True, exclusive=False, auto_delete=False)
        print 'MQServer is running...'
        self.ch.wait()
        pass

if __name__ == '__main__':
    server = MQServer(mq_user=SipMqConstants.MQ_USER, mq_password=SipMqConstants.MQ_PASSWORD)
    pass
