from sim import MSSimObject
from utilization.cpu import *
from utilization.vm import *

def get_process_by_name(process_name):
	for subprocess in Process.subclasses:
		if process_name.lower() == subprocess.__name__.lower():
			return subprocess
	return None

def get_process_list():
	process_names = []
	for subprocess in Process.subclasses:
		process_names.append(subprocess.__name__)
	return process_names

class Process(MSSimObject):
	subclasses = []

	def __init__(self):
		super().__init__()
		self.t_name = "AbstractProcess"

	def __init_subclass__(cls, **kwargs):
		super().__init_subclass__(**kwargs)
		cls.subclasses.append(cls)

	def __str__(self):
		return self.t_name

	# Abstract function	
	def execute(self,packet):
		pass

class Forwarding(Process):

	def __init__(self):
		super().__init__()
		self.t_name = "ForwardingProcess"
		self.metrics["forwarded_packets"] = 0

	def execute(self,packet):
		self.metrics["forwarded_packets"] += 1

class Database(Process):

	def __init__(self):
		Process.__init__(self)
		vm_bytes=1024000 * 320
		self.vm = VM(method="zero-one",vm_bytes=vm_bytes) #MB
		self.conf["database_requests"] = 0
		self.children["VM"] = self.vm

	def execute(self,packet):
		self.conf["database_requests"] += 1
		self.vm.utilize_vm() 
		# requires hdd operations and randomness

class Authentication(Process):

	def __init__(self):
		super().__init__()
		self.t_name = "ProxyToProxyProcess"
		self.vm = VM(method="ror",vm_bytes=1024000*64) #MB
		self.conf["authentications"] = 0
		self.children["VM"] = self.vm

	def execute(self,packet):
		self.conf["authentications"] += 1
		self.vm.utilize_vm() 

class MemoryCacheOperation(Process):

	def __init__(self):
		super().__init__()
		self.t_name = "CacheProcess"
		vm_bytes=1024*1280000
		self.vm = VM(method="walk-0a",vm_bytes=vm_bytes)
		self.children["VM"]=self.vm

	def execute(self,packet):
		self.vm.utilize_vm()

class Compute(Process):

	def __init__(self):
		super().__init__()
		self.t_name = "ComputeProcess"
		self.cpu = CPU(method="nsqrt",max_ops=10)
		self.children["CPU"]=self.cpu

	def execute(self,packet):
		self.cpu.utilize_cpu()

class ComputeDatabaseResponse(Process):
	def __init__(self):
		super().__init__()
		self.t_name = "ComputeDatabaseResponseProcess"
		vm_bytes= 1024*8000
		self.cpu = CPU(method="nsqrt",max_ops=10)
		self.vm = VM(method="flip",vm_bytes=vm_bytes)
		self.children["CPU"]=self.cpu
		self.children["VM"]=self.cpu
		Process().__init__()

	def execute(self,packet):
		self.cpu.utilize_cpu()
		self.vm.utilize_vm()


class LocalCompute(Process):

	def __init__(self):
		super().__init__()
		self.t_name = "LocalComputeProcess"
		self.cpu = CPU(method="nsqrt",max_ops=5)
		self.children["CPU"]=self.cpu

	def execute(self,packet):
		self.cpu.utilize_cpu()
