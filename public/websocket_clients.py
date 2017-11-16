# -*- coding:utf-8 -*-
"""__author__ = 'Lijiazhu'"""
import json
import logging
import thread
import threading
import time
import traceback

import websocket
from ConstantSet import Constant
from websocket import WebSocketConnectionClosedException


class WebSocketClient(threading.Thread):
    def __init__(self, user_num, basic_token, user_pool, p_stop_signal, log_name="MXTest"):
        threading.Thread.__init__(self)
        self._logger = logging.getLogger(log_name)
        self._handlers = []
        self.user_num = user_num
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.ws = None
        #self.notifies = []
        self.basic_token = basic_token
        self.lock = threading.Lock()
        self.running_state = False

    def set_basic_token(self, basic_token):
        self.basic_token = basic_token

    def add_handler(self, handler):
        self._handlers.append(handler)
        return self

    def sub_handler(self, handler):
        self._handlers.remove(handler)
        return self

    def fire(self, **kwargs):
        for handler in self._handlers:
            handler(**kwargs)

    def on_message(self, ws, message):
        try:
            json_data = json.loads(message)
            #self.notifies.append(json_data)
            body = json_data.get("event", {})
            notify_id = body.get("id", "")
            # notify_name = body.get("name", "")
            # notify_msg_type = body.get("msg_type", "")
            self._logger.info(str(self.user_num)+message)
            notify = {"type": "notify_res",
                      "id": notify_id}
            send_h = json.dumps(notify)
            try:
                ws.send(send_h)
            except WebSocketConnectionClosedException:
                if self.running_state:
                    self._logger.error("The webSocket is off.")
                else:
                    self._logger.info("WebSocket is closed normally.")

            self.fire(message=message, user_num=self.user_num, basic_token=self.basic_token)
        except Exception as e:
            print e
            self._logger.critical("The webSocket has an exception "+str(traceback.format_exc()))

    def on_error(self, ws, error):
        self._logger.critical("WebSocket has an error " + str(error))

    def on_close(self, ws):
        #time.sleep(3)
        try:
            if self.running_state:
                self._logger.info("WebSocket ### exception closed ###")
                websocket.enableTrace(False)
                # WebSocket.enableTrace(True)
                # 是否打印日志到屏幕
                # print ("Run WebSocketThread")
                self.ws = websocket.WebSocketApp(Constant.WS_URL,
                                                 keep_running=True,
                                                 on_message=self.on_message,
                                                 on_error=self.on_error,
                                                 on_close=self.on_close)
                self.ws.on_open = self.on_open
                self.ws.run_forever()
            else:
                self._logger.info("WebSocket ### normal closed ###")
        except:
            self._logger.info("WebSocket ### aqf except closed ###")


    def on_open(self, ws):
        auth_req = {"type": "identify_req",
                    "token": self.basic_token,
                    "platform": "mobile-android"}
        params = json.dumps(auth_req)

        ws.send(params)
        heart_req = {"type": "heartbeat"}
        heart_params = json.dumps(heart_req)

        def run(*args):
            time_sleep = 0
            while not self.p_stop_signal.is_set():
                try:
                    time_sleep += 1
                    time.sleep(1)
                    # time.sleep(30)
                    if time_sleep == 30:
                        ws.send(heart_params)
                        if self.user_pool.cache_lock.locked():
                            self._logger.debug("addd:*******************************************")
                        time_sleep = 0
                except WebSocketConnectionClosedException:
                    break
                except:
                    print traceback.format_exc()
                    print self.user_num

            # self.running_state = False
            # self.ws.close()
        thread.start_new_thread(run, ())

    def run(self):
        try:
            self.running_state = True
            websocket.enableTrace(False)
            # WebSocket.enableTrace(True)
            # 是否打印日志到屏幕
            # print ("Run WebSocketThread")
            self.ws = websocket.WebSocketApp(Constant.WS_URL, keep_running=True,
                                             on_message=self.on_message,
                                             on_error=self.on_error,
                                             on_close=self.on_close)
            self.ws.on_open = self.on_open
            self.ws.run_forever()
        except:
            self._logger.error(traceback.format_exc())

    def stop(self):
        try:
            if isinstance(self.ws, websocket.WebSocketApp):
                self.running_state = False
                self.ws.close()
        except:
            self._logger.info("WebSocket ### aqf except closed ###")

if __name__ == '__main__':
    pass
