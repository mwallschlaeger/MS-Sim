import time, math, random
from sim import MSSimObject

import importlib.util
spec = importlib.util.spec_from_file_location("stress_ng", "stress-ng/bindings/stress_ng.py")
stress_ng = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stress_ng)


class CPU(MSSimObject):
	
	t_name = "CPU_Stress"
	''' max_ops = number of loops to run 
		method = stress-ng cpu method to execute '''
	def __init__(self,max_ops=3,method=""):
		self.conf["max_ops"] = max_ops
		self.conf["method"] = method
		self.metrics["perfomed_operations"] = 0
		self.metrics["failed_operations"] = 0
		super().__init__()

	def __str__(self):
		return "CPU" # TODO

	def get_methods(self):
		return stress_ng.CPU_METHODS

	''' recommended '''
	def utilize_cpu(self):
		result = stress_ng.stress_cpu(method=self.conf["method"],max_ops=self.conf["max_ops"])
		if result == 0:
			self.metrics["perfomed_operations"] += self.conf["max_ops"]
		else:
			self.metrics["failed_operations"] += self.conf["max_ops"]		
		return result

	''' not recommended '''
	def utilize_cpu_ms_sim(self):
		for i in range(self.__conf["max_ops"]):
			result = stress_ng.ms_sim_stress_cpu(method=self.conf["method"],max_ops=self.conf["max_ops"])
			if result == 0:
				self.metrics["perfomed_operations"] += self.conf["max_ops"]
			else:
				self.metrics["failed_operations"] += self.conf["max_ops"]
			time.sleep(0.1)
		return 0
