import logging
import os
import sys
import pprint
import queue
import multiprocessing

from utilization.thread_worker import ThreadWorker
from utilization.multiprocessing_worker import MultiprocessingWorker

TCP_NETWORK_PROTOCOL ="TCP"
AVAILABLE_NETWORK_TYPES = [TCP_NETWORK_PROTOCOL]

import os
ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

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
	
def get_queue(multiprocessing_worker=False,maxsize=1000):
	if multiprocessing_worker:
		return multiprocessing.Queue(maxsize=maxsize) 
	else:
		return  queue.Queue(maxsize=maxsize) 
	
def spawn_worker(t_name,
				incoming_pipeline,
				outgoing_pipeline,
				default_process,
				multiprocessing_worker=False):
	
	if multiprocessing_worker:
		return MultiprocessingWorker(
			t_name=t_name,
			incoming_pipeline=incoming_pipeline,
			outgoing_pipeline=outgoing_pipeline,
			default_process=default_process)
	else:
		return ThreadWorker(
			t_name=t_name,
			incoming_pipeline=incoming_pipeline,
			outgoing_pipeline=outgoing_pipeline,
			default_process=default_process)

def worker_parm_check(t_name,min_wait,max_wait):
	ok = True
	if (min_wait>max_wait):
		logging.debug(
			"{}: Worker initialized with bad parameters, \
			min_random_wait_to_read must be smaller than \
			max_random_wait_to_read but {} > {}".format(
								t_name,
								min_wait,
								max_wait))
		ok = False
	return ok

# TODO TEST
def log_metrics(ms_obj=[],print_header=False,file_obj=None):
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
	if file_obj != None:
		file_obj.write(s+"\n")
		file_obj.flush()
	else:
		logging.info(s)

def print_leafs(ms_obj=[]):
	pp = pprint.PrettyPrinter(indent=5)
	for i in ms_obj:
		structure[i.t_nme] = i.get_leaf()
	pp.print(structure)