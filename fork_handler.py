import logging
from sim import MSSimObject

##############
# FORKS List #
##############

# a list of possible ways to handle incoming packets, each fork is defined by a probability and a pipeline.
# last entry in fork_list should have a 100 probability. Else packet will not be handled and forgotten (anomaly?) 

class ForkHandler(MSSimObject):

	def __init__(self):
		super().__init__()
		self.t_name = "ForkHandler"
		self.conf["fork_list"] = []
		self.metrics["fork_list_errors"] = 0

	def __str__(self):
		return "{}: {}".format(self.t_name, self.conf["fork_list"])

	def remove_fork(self,pos):
		try:
			self.conf["fork_list"].remove(pos)
		except Exception as FL2:
			self.metrics["fork_list_errors"] += 1
			logging.warning("Could not remove element {} from fork_list".format(pos))
			logging.warning("{}".format(str(FL2)))
			return -1

	def add_fork(self,pipeline,probability,pos=0):
		if pos==-1:
			# add at end of list
			self.conf["fork_list"].append((probability,pipeline))
		try:
			self.conf["fork_list"].insert(pos,(probability,pipeline))
		except Exception as FL1:
			self.metrics["fork_list_errors"] += 1
			logging.warning("Could not insert fork to positon {} in fork list of Source {}".format(str(pos),str(self)))
			logging.warning("{}".format(str(FL1)))

	def get_fork(self,pos):
		if pos==-1:
			return self.conf["fork_list"][len(self.conf["fork_list"])-1]
		try:
			return self.conf["fork_list"][pos]
		except Exception as FL3:
			self.metrics["fork_list_errors"] += 1
			logging.warning("Fork Element {} in {}, not found".format(pos,self.__str__()))
			logging.warning("{}".format(str(FL1)))
			return None

	def set_default_fork_pipeline(self,pipeline,probability=100):
		self.conf["fork_list"][len(self.conf["fork_list"])-1] = (100,pipeline)

	def get_forks(self):
		return self.conf["fork_list"]

	def set_forks(self,forks):
		self.conf["fork_list"] = forks

	def change_fork_probability(pos,new_probability):
		prob,pipeline = self.conf["fork_list"][pos]
		self.conf["fork_list"] = (new_probability,pipeline)
