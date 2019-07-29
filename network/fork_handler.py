import logging,copy,random
from sim import MSSimObject

class ForkHandler(MSSimObject):

	def __init__(self):
		super().__init__()
		self.t_name = "ForkHandler"
		self.conf["fork_list"] = []
		self.conf["noop_probability"] = 100
		self.metrics["fork_l_errors"] = 0

	def __str__(self):
		return "{}: {}".format(self.t_name, self.conf["fork_list"])

	def fork_check(self,fork_list):
		sum_probability = 0
		for probability,__ in self.conf["fork_list"]:
			sum_probability += probability
		if sum_probability <= 100:
			self.conf["noop_probability"] = 100 - sum_probability
			return True
		return False

	def get_random_pipeline(self):
		r = random.randint(0,100)
		curr_probability = 0
		for probability,pipeline in self.conf["fork_list"]:
			if r <= curr_probability + probability :
				return pipeline
			curr_probability += probability
		return None

	def remove_fork(self,pos):
		old_fork_list = copy.copy(self.conf["fork_list"])
		
		if pos >= len(self.conf["fork_list"]):
			self.metrics["fork_l_errors"] +=1
			logging.warning("{}: fork list only has {} elements, unable to delete element {}".format(str(self),len(self.conf["fork_list"]),pos))
			return False		
		self.conf["fork_list"].pop(pos)

		if not self.fork_check(self.conf["fork_list"]):
			self.conf["fork_list"] = old_fork_list
			return False
		return True
		
	def add_fork(self,pipeline,probability,pos=0):
		old_fork_list = copy.copy(self.conf["fork_list"])

		try:
			self.conf["fork_list"].insert(pos,(probability,pipeline))
		except Exception as FL1:
			self.metrics["fork_l_errors"] += 1
			logging.warning("Could not insert fork to positon {} in fork list of Source {}".format(str(pos),str(self)))
			logging.warning("{}".format(str(FL1)))

		if not self.fork_check(self.conf["fork_list"]):
			self.conf["fork_list"] = old_fork_list
			return False
		return True

	def get_noop_probability(self):
		return self.conf["noop_probability"]

	def get_fork(self,pos):
		try:
			return self.conf["fork_list"][pos]
		except Exception as FL3:
			self.metrics["fork_l_errors"] += 1
			logging.warning("Fork Element {} in {}, not found".format(pos,self.__str__()))
			logging.warning("{}".format(str(FL3)))
			return None

	def get_forks(self):
		return self.conf["fork_list"]

	def set_forks(self,forks):
		old_fork_list = copy.copy(self.conf["fork_list"])
		
		self.conf["fork_list"] = forks

		if not self.fork_check(self.conf["fork_list"]):
			self.conf["fork_list"] = old_fork_list
			return False
		return True

	def change_fork_probability(pos,new_probability):
		old_fork_list = copy.copy(self.conf["fork_list"])
	
		prob,pipeline = self.conf["fork_list"][pos]
		self.conf["fork_list"] = (new_probability,pipeline)

		if not self.fork_check(self.conf["fork_list"]):
			self.conf["fork_list"] = old_fork_list
			return False
		return True
