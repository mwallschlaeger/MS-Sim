import threading
import logging
import multiprocessing

class MSSimObject():

	def __init__(self):
		self.t_name = "MSSimObject"
		self.conf = {}
		self.metrics = {}
		self.const_metrics = {}
		self.children = {}

	def __str__(self):
		return self.t_name

	def get_metrics(self):
		return self.metrics

	def get_children(self):
		return self.children

	def get_conf(self):
		return self.conf

	def get_t_name(self):
		return self.t_name

	def get_metrics(self,name_value_tuple_list=None):
		n_v_list = []
		if name_value_tuple_list is not None:
			n_v_list = name_value_tuple_list

		for k,v in self.metrics.items():
			n_v_list.append((type(self).__name__ + "_" + k,v))

		for child,v in self.children.items():
			for k,v in v.metrics.items():
				n_v_list.append((type(self.children[child]).__name__ + "_" + k,v))
		return n_v_list

	def get_leaf(self,reset_metrics=False):
		leaf = {}
		leaf["name"] = self.t_name
		leaf["conf"] = self.conf
		leaf["metrics"] = self.metrics
		leaf["children"] = {}
		for k,v in self.children.items():
			leaf["children"][k] = self.children[k].get_leaf()
		return leaf

	def reset_metrics(self):
		for k in self.metrics.keys():
			if not k.startswith("const") and not k.startswith("list"):
				self.metrics[k] = 0
			if k.startswith("list"):
				self.metrics[k] = []
			for child,v in self.children.items():
				self.children[child].reset_metrics()

class MSSimThread(threading.Thread,MSSimObject):

	t_name = "MSSimThread"

	def __init__(self):
		MSSimObject.__init__(self)
		threading.Thread.__init__(self)

class MSSimMultiProcessing(multiprocessing.Process,MSSimObject):

	t_name = "MSSimThread"

	def __init__(self):
		MSSimObject.__init__(self)
		multiprocessing.Process.__init__(self)