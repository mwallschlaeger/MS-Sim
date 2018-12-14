

class MSSimObject():

	t_name = "MS-Sim-Object"
	conf = {}
	metrics = {}
	children = {}

	def __init__(self):
		pass

	def get_metrics(self):
		return self.metrics

	def get_children(self):
		return self.children

	def get_conf(self):
		return self.conf

	def get_t_name(self):
		return self.t_name

	def get_leaf(self):
		leaf = {}
		leaf["name"] = self.t_name
		leaf["conf"] = self.conf
		leaf["metrics"] = self.metrics
		leaf["children"] =self.children
		for c in children:
			leaf["children"][c.get_t_name()] = c.get_leaf()

	def __reset_metrics(self):
		for k,v in leaf["metrics"].items():
			v = 0