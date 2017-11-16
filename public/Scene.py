# coding:utf-8
from Step import Step
import yaml
import logging


class Scene(object):
    """定义场景类，把分析yaml文件生成的json对象传递过来，
       根据json对象生成Step类列表
       在一个yaml文件生成的列表中上下串行执行
    """
    def __init__(self, scene_yaml_file, user_pool, p_stop_signal, log_name="MXTest"):
        self.scene_yaml_file = scene_yaml_file
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.scene_yaml = None
        self.scene_step_list = None
        self._logger = logging.getLogger(log_name)

    def run(self):
        # 这里应该是根据StepList 解析出StepFeature
        # todo  这里判断一下对象是否是List对象
        with open(self.scene_yaml_file) as f:
            self._logger.info("open "+str(self.scene_yaml_file)+" success!")
            self.scene_yaml = yaml.load(f)
            self._logger.info("yaml file: " + str(self.scene_yaml))

            if isinstance(self.scene_yaml, dict) and "scene_step_list" in self.scene_yaml:
                self.scene_step_list = self.scene_yaml["scene_step_list"]
            else:
                self._logger.warning("Scene yaml file is not dictionary type data, or does not exist scene_step_list!")

            range_times = 1
            if "scene_range" in self.scene_yaml:
                range_times = self.scene_yaml["scene_range"]
                self._logger.info(str(self.scene_yaml["scene_name"]) +
                                  "The scene needs to be executed "+str(range_times)+" times")

            if "total_members" in self.scene_yaml and "member_state" in self.scene_yaml:
                self._logger.info(str(self.scene_yaml["scene_name"]) +
                                  "The scene needs " + str(self.scene_yaml["total_members"]) +
                                  " user participation，The user's initial status is "+
                                  str(self.scene_yaml["member_state"]))

            for i in range(range_times):
                self._logger.info("scene Cycle " + str(i+1)+" times;  The total number of cycles is "+str(range_times))
                if isinstance(self.scene_step_list, list):
                    step_time = 0
                    for step in self.scene_step_list:
                        step_time += 1
                        self._logger.debug(str(step_time) + str(self.user_pool.user_phone_num_list))
                        self._logger.info("scene Cycle" + str(step_time) + " steps;" + str(step))
                        tmp_step = Step(step, self.user_pool, self.p_stop_signal)
                        tmp_step.run()
                else:
                    # todo 抛出配置文件错误异常
                    self._logger.warning("Profile exception!")

            self._logger.info(str(self.scene_yaml["scene_name"]) + " scene is finished.")
