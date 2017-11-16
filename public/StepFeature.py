# coding:utf-8
from ExecuteCase import ExecuteCase
import threading
import logging
import time
import copy


class StepFeature(object):
    """根据传递过来的一个StepFeature key-Value值来解析下一步执行操作
       如果isInheritScence == True:标明是继承自其他yaml文件的一个操作，则在这一步操作中，解析yaml文件，循环流程
       如果是继承的话 则有test_inherit key,value 为对应的文件名
       如果不是继承的话 则有 test_action key,value 为对应的Action类的类名
       如果isInheritScence == False:则根据actionName 属性判断是那个Action类，生成该类的对象，执行Action
    """
    def __init__(self, step_feature, user_pool, p_stop_signal, log_name="MXTest"):
        self.step_feature = step_feature
        self.user_pool = copy.copy(user_pool)
        self.p_stop_signal = p_stop_signal
        self._logger = logging.getLogger(log_name)

    def run(self):
        # self._logger.debug("Group_id_list" + str(self.user_pool.group_id_list))
        if not isinstance(self.step_feature, dict):
            self._logger.warning("Not a dictionary!")
            return
        delay_time = 0

        if "delay_time" in self.step_feature:
            delay_time = self.step_feature["delay_time"]

        caps = 1
        if "caps" in self.step_feature:
            caps = self.step_feature["caps"]

        multiple = 1
        if "multiple" in self.step_feature:
            multiple = self.step_feature["multiple"]

        self._logger.debug("caps:"+str(caps)+" multiple:"+str(multiple)+" delay_time:"+str(delay_time))

        multiple_step_feature_thread_list = []
        for multiple_i in range(multiple):
            step_feature_thread = self._StepFeatureThread(self.step_feature, self.user_pool, self._logger,
                                                          self.p_stop_signal, multiple_i)
            multiple_step_feature_thread_list.append(step_feature_thread)

        for i in range(len(multiple_step_feature_thread_list)):
            multiple_step_feature_thread_list[i].start()
            time.sleep(delay_time)

        for i in range(len(multiple_step_feature_thread_list)):
            multiple_step_feature_thread_list[i].join()

    class _StepFeatureThread(threading.Thread):
        def __init__(self, step_feature, user_pool, _logger, p_stop_signal, wait_time=0):
            threading.Thread.__init__(self)
            self.step_feature = step_feature
            self.user_pool = user_pool
            self.p_stop_signal = p_stop_signal
            self.wait_time = wait_time
            self._logger = _logger

        def run(self):
            caps = 1
            if "caps" in self.step_feature:
                caps = self.step_feature["caps"]
            #sleep_time = 1.0 / caps
            if "inherit" in self.step_feature:
                self._logger.debug("This is an inheritance file:" + str(self.step_feature["inherit"]))
                from Scene import Scene
                yaml_file_path = self.step_feature["inherit"]
                scene_thread_list = []
                signal = threading.Event()
                self._logger.debug("caps：" + str(caps))
                # "每个并发需要用户：" + str(self.step_feature["executor_num"]))
                for i in xrange(caps):
                    one_scene_thread = self._SceneThread(yaml_file_path, self.user_pool, signal, self.p_stop_signal)
                    scene_thread_list.append(one_scene_thread)

                for one_scene_thread in scene_thread_list:
                    one_scene_thread.start()
                    #time.sleep(sleep_time)

                signal.set()
                for one_scene_thread in scene_thread_list:
                    one_scene_thread.join()

            elif "action" in self.step_feature:
                self._logger.debug("这是一个Action" + str(self.step_feature["action"]))

                action_thread_list = []
                signal = threading.Event()
                self._logger.debug("caps：" + str(caps))
                # " 每个并发需要用户数：" + str(self.step_feature["executor_num"]))
                for i in xrange(caps):
                    one_action_thread = self._UserThread(self.step_feature, self.user_pool, signal, self.p_stop_signal)
                    action_thread_list.append(one_action_thread)

                for one_action_thread in action_thread_list:
                    one_action_thread.start()
                    #time.sleep(sleep_time)

                signal.set()
                for one_action_thread in action_thread_list:
                    one_action_thread.join()

        class _SceneThread(threading.Thread):
            def __init__(self, yaml_file_path, user_pool, signal, p_stop_signal):
                threading.Thread.__init__(self)
                self.yaml_file_path = yaml_file_path
                self.p_stop_signal = p_stop_signal
                self.user_pool = copy.copy(user_pool)
                self.signal = signal

            def run(self):
                from Scene import Scene
                case_executor = Scene(self.yaml_file_path, self.user_pool, self.p_stop_signal)
                self.signal.wait()
                case_executor.run()

        class _UserThread(threading.Thread):
            def __init__(self, case_info_dict, user_pool, signal, p_stop_signal):
                threading.Thread.__init__(self)
                self.case_info_dict = case_info_dict
                self.user_pool = user_pool
                self.p_stop_signal = p_stop_signal
                self.signal = signal

            def run(self):
                case_executor = ExecuteCase(self.case_info_dict, self.user_pool, self.p_stop_signal)
                self.signal.wait()
                case_executor.execute_case()
