from sim import MSSimObject

class Process(MSSimObject):

	def __init__(self):
		super().__init__()
		self.t_name = "AbstractProcess"

	def __str__(self):
		return self.t_name

	# Abstract function	
	def execute(self,device_id,request_id):
		pass

class ForwardingProcess(Process):

	def __init__(self):
		super().__init__()
		self.t_name = "ForwardingProcess"
		self.metrics["forwarded_packets"] = 0

	def execute(self,device_id,request_id):
		self.metrics["forwarded_packets"] += 1
