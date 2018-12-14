import time, math, random
from sim import MSSimObject

import importlib.util
spec = importlib.util.spec_from_file_location("stress_ng", "stress-ng/bindings/stress_ng.py")
stress_ng = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stress_ng)


class VM(MSSimObject):
	
	t_name = "VM_Stress"
	''' utilization = number of loops to run 
		method = stress-ng cpu method to execute
	'''
	def __init__(self,method="",vm_bytes=4096*1000,max_ops=1):
		self.conf["max_ops"] = max_ops
		self.conf["vm_bytes"] = vm_bytes
		self.conf["method"] = method
		self.metrics["executions"] = 0
		self.metrics["affacted_bytes"] = 0
		self.metrics["byte_failures"] = 0
		super().__init__()

	def __str__(self):
		return "VM" # TODO

	def get_methods(self):
		return stress_ng.VM_METHODS

	''' recommeded '''
	def utilize_vm(self):
		result = stress_ng.stress_vm(method=self.conf["method"],vm_bytes=self.conf["vm_bytes"] )
		self.metrics["executions"] += 1
		if result == 0:
			self.metrics["affacted_bytes"] += self.conf["vm_bytes"]
		else:
			self.metrics["byte_failures"] += self.conf["vm_bytes"]
		return result

	''' not recommended '''
	def utilize_vm_ms_sim(self):
		for i in range(self.conf["max_ops"]):
			result = stress_ng.ms_sim_stress_vm(method=self.conf["method"],vm_bytes=self.conf["vm_bytes"] )
			self.metrics["executions"] += 1
			if result == 0:
				self.metrics["affacted_bytes"] += self.conf["vm_bytes"]
			else:
				self.metrics["byte_failures"] += self.conf["vm_bytes"]
			time.sleep(0.1)
		return 0
