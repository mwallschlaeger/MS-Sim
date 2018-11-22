import logging 
class LoadBalancer():
	
	def __init__(self,host_list=[]):
		
		try:
			for i in range(host_list):
				h,d = host_list[i]
				if not self.parm_check(h,b):
					del host_list[i]
					logging.info("removed wrong element from provided Host/Port {}/{} tuple for LoadBalancer ...".format(h,b))
		except:
			logging.info("Host/Port list provided, not in correct format, expect (host,port) tuple ...")
			self.host_list = []
			return 

		self.host_list=host_list

	def __str__(self):
		return "Abstract_Loadbalancer"


	def parm_check(self,hostname,port):
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

	@abstractmethod
	def get_next_endpoint():
		pass

class RoundRobinLoadBalancer(LoadBalancer):

	def __init__(self):
		last = 0
		super().__init__()

	def __str__(self):
		return "RR_Loadbalancer"

	def get_next_endpoint():
		next= last+1
		if next > len(self.host_list):
			last = 0 
			return host_list[0]