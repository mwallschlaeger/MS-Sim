import logging 
import string

from sim import MSSimObject

class LoadBalancer(MSSimObject):
	
	def __init__(self,host_list=[]):
		super().__init__()
		self.t_name = "AbstractLoadBalancer"
		
		if (self.check_host_list(host_list)):
			self.conf["host_list"]=host_list
		else:
			self.conf["host_list"] = []
			self.metrics["const_host_list_len"] = len(self.conf["host_list"])

	def check_host_list(self,host_list=[]):
		
		for i in range(len(host_list)):
			try:
				h,d = host_list[i]
			except:
				logging.debug("Host/Port list provided, not in correct format, expect (host,port) tuple ...")
				return False
			
			if not self.parm_check(h,d):
				del host_list[i]
				logging.debug("removed wrong element from provided Host/Port {}/{} tuple for LoadBalancer ...".format(h,b))
		return True 

	def parm_check(self,hostname,port):
		try:
			basestring
		except NameError:
			basestring = str
		if not isinstance(hostname, basestring):
			return False
		if not isinstance(port,int):
			return False
		return True

	def add_host(self,hostname,port):
		if self.parm_check(hostname,port):
			self.conf["host_list"].append((hostname,port))
			self.metrics["const_host_list_len"] = len(self.conf["host_list"])
			return True
		return False

	def delete_host(self,hostname,port):
		if self.parm_check(hostname,port):
			for i in range(self.conf["host_list"]):
				h,p = self.conf["host_list"][i]
				if hostname == h: 
					if port == p:
						del self.conf["host_list"][i]
						self.metrics["const_host_list_len"] = len(self.conf["host_list"])

	def get_host_list(self):
		return self.conf["host_list"]
	
	def set_host_list(self,lst=[]):
		if self.check_host_list(lst):
			self.conf["host_list"] = lst
			return True
		else: 
			return False

	# abstract method
	def get_next_endpoint(self):
		pass

class RoundRobinLoadBalancer(LoadBalancer):

	def __init__(self,host_list=[]):
		LoadBalancer.__init__(self,host_list)
		self.t_name = "RoundRobinLoadBalancer"
		self.current = 0

	def get_next_endpoint(self):
		if not len(self.conf["host_list"]) > 0:
			return None

		self.current+=1
		if self.current >= len(self.conf["host_list"]):
			self.current = 0
		return self.conf["host_list"][self.current]