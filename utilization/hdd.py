import time, math, random
from sim import MSSimObject

import importlib.util
spec = importlib.util.spec_from_file_location("stress_ng", "stress-ng/bindings/stress_ng.py")
stress_ng = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stress_ng)


class HDD(MSSimObject):
	
	''' utilization = number of loops to run 
		method = stress-ng cpu method to execute
	'''
	def __init__(self,method="",hdd_bytes=4096*1000,max_ops=1):
		super().__init__()
		self.t_name = "HDD_Stress"
		self.conf["max_ops"] = max_ops
		self.conf["hdd_bytes"] = hdd_bytes
		self.conf["method"] = method
		self.metrics["executions"] = 0
		self.metrics["affacted_bytes"] = 0
		self.metrics["byte_failures"] = 0

	def __str__(self):
		return "HDD" # TODO

	def get_methods(self):
		return stress_ng.HDD_METHODS

	''' recommeded '''
	def utilize_hdd(self):
		result = stress_ng.stress_hdd(method=self.conf["method"],hdd_bytes=self.conf["hdd_bytes"], max_ops = self.conf["max_ops"] )
		self.metrics["executions"] += 1
		if result == 0:
			self.metrics["affacted_bytes"] += self.conf["hdd_bytes"]
		else:
			self.metrics["byte_failures"] += self.conf["hdd_bytes"]
		return result

hdd = HDD(method="wr-seq",hdd_bytes=1024 * 400000, max_ops= 10)
hdd.utilize_hdd()