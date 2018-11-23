import logging , string
class LoadBalancer():
	
	def __init__(self,host_list=[]):
		
		if (self.check_host_list(host_list)):
			self.host_list=host_list
		else:
			self.host_list = []


	def __str__(self):
		return "Abstract_Loadbalancer"


	def check_host_list(self,host_list=[]):
		
		for i in range(len(host_list)):
			try:
				h,d = host_list[i]
			except:
				logging.error("Host/Port list provided, not in correct format, expect (host,port) tuple ...")
				return False
			
			if not self.parm_check(h,d):
				del host_list[i]
				logging.warning("removed wrong element from provided Host/Port {}/{} tuple for LoadBalancer ...".format(h,b))
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
			self.host_list.append((hostname,port))
			return True
		return False

	def delete_host(self,hostname,port):
		if self.parm_check(hostname,port):
			for i in range(self.host_list):
				h,p = self.host_list[i]
				if hostname == h: 
					if port == p:
						del self.host_list[i]

	def get_next_endpoint(self):
		pass

class RoundRobinLoadBalancer(LoadBalancer):

	def __init__(self,host_list=[]):
		self.current = 0
		LoadBalancer.__init__(self,host_list)

	def __str__(self):
		return "RR_Loadbalancer"

	def get_next_endpoint(self):
		if not len(self.host_list) > 0:
			return None

		self.current+=1
		if self.current >= len(self.host_list):
			self.current = 0
		return self.host_list[self.current]