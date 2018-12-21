import logging, os, sys, pprint

def configure_logging(debug,filename=None):
	if filename is None:
		if debug:
			logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)
		else:
			logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
	else:
		if debug:
			logging.basicConfig(filename=filename,format='%(asctime)s %(message)s', level=logging.DEBUG)
		else:
			logging.basicConfig(filename=filename,format='%(asctime)s %(message)s', level=logging.INFO)
	
def print_metrics(ms_obj=[],print_header=False):
	n_v_list = []
	s = ""
	for i in ms_obj:
		l = i.get_metrics(n_v_list)
		for n,v in l:
			if print_header:
				s = "{},{}".format(s, n)
			else:
				if s == "":
					s = "{}".format(v)
				s = "{},{}".format(s, v)

	print(s)

def print_leafs(ms_obj=[]):
	pp = pprint.PrettyPrinter(indent=5)
	for i in ms_obj:
		structure[i.t_nme] = i.get_leaf()
	pp.print(structure)