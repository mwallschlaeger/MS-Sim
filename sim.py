

class MS-Sim-Object():

	def __init__(self):
		self.__t_name = {}
		self.__conf = {}
		self.__metrics = {}
		self.__children = {}

	def __get_metrics(self):
		return self.__metrics

	def __get_children(self):
		return self.__children

	def __get_conf(self):
		return self.__conf

	def __get_t_name(self):
		return self.__t_name

	def __get_leaf(self):
		leaf = {}
		leaf["conf"] = self.__conf
		leaf["metrics"] = self.__metrics
		leaf["children"] =self.__children
		for c in children:
			leaf["children"][c.__get_t_name()] = c.__get_leaf()
		