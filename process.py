from sim import MSSimObject

class Process(MSSimObject):

	t_name = "AbstractProcess"

	def __init__(self):
		pass

	def __str__(self):
		return self.t_name

	# Abstract function	
	def execute(self,device_id,request_id):
		pass

class ForwardingProcess(Process):

	t_name = "ForwardingProcess"

	def __init__(self,t_name):
		self.t_name = t_name
		self.metrics["forwarded_packets"] = 0


	def execute(self,device_id,request_id):
		self.metrics["forwarded_packets"] += 1
