# coding:utf-8
import logging
import threading
from StepFeature import StepFeature


class Step(object):
    def __init__(self, step_feature_list, user_pool, p_stop_signal, log_name="MXTest"):
        self.step_feature_list = step_feature_list
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self._logger = logging.getLogger(log_name)

    def run(self):
        if not isinstance(self.step_feature_list, list):
            """抛出配置文件异常的错误"""
            self._logger.warning(self.step_feature_list)
            return False
        self._logger.info(str(self.user_pool.user_phone_num_list))

        step_feature_thread_list = []
        signal = threading.Event()
        for step_feature in self.step_feature_list:
            one_step_feature_thread = self.EachFeatureThread(step_feature, self.user_pool, signal, self.p_stop_signal)
            step_feature_thread_list.append(one_step_feature_thread)

        for i in range(len(step_feature_thread_list)):
            step_feature_thread_list[i].start()

        signal.set()
        for i in range(len(step_feature_thread_list)):
            step_feature_thread_list[i].join()

    class EachFeatureThread(threading.Thread):
        def __init__(self, step_feature, user_pool, signal, p_stop_signal, log_name="MXTest"):
            threading.Thread.__init__(self)
            self.step_feature = step_feature
            self.user_pool = user_pool
            self.signal = signal
            self.p_stop_signal = p_stop_signal
            self._logger = logging.getLogger(log_name)

        def run(self):
            self._logger.debug("EachFeatureThread" + str(self.step_feature))
            each_step_feature = StepFeature(self.step_feature, self.user_pool, self.p_stop_signal)
            self.signal.wait()
            each_step_feature.run()
