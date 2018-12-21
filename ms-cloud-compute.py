#!/usr/bin/python3

import argparse, time, logging, queue, sys, random, threading, signal, os
from listen_network_interface import ListenNetworkInterface
from send_network_interface import SendNetworkInterface
from load_balancer import RoundRobinLoadBalancer
from cpu import CPU
from vm import VM
from process import Process, ForwardingProcess
from worker import Worker
import helper

RUNNING = True # controls main loop
ELEMENTS = []
t_name = "MS-CLOUD-COMPUTE"

def sig_int_handler(signal, frame):

	global RUNNING
	global ELEMENTS

	if RUNNING == False:
		os.kill(signal.CTRL_C_EVENT, 0)
	RUNNING = False
	for e in ELEMENTS:
		e.stop()
		
def main():
	global ELEMENTS
	signal.signal(signal.SIGINT, sig_int_handler)

	parser = argparse.ArgumentParser()
	
	# cloud compute
	parser.add_argument("-listen_port",type=int, default=5093,help="Port to listen for incoming messages")
	parser.add_argument("-database",action='append',help="a Database node to interact with",required=True)
	parser.add_argument("-database_port",type=int,default=5094,help="Port the database nodes are listening on")
	parser.add_argument("-max_clients",type=int,default=5000,help="maximum number of clients connected to Cloud Compute")
	parser.add_argument("-queue_size",type=int,default=5000,help="Size of interal processing queue")
	parser.add_argument("-cached_percentile",type=int,default=20,help="Percentile of request answered from cache")
	parser.add_argument("-database_request_percentile",type=int,default=50,help="Percentile of requests further request database (calculated after caching)")

	# general 
	parser.add_argument("-cleaning_interval",type=int,default=2,help="interval in which broken connections got cleared",metavar='2')

	# logging
	parser.add_argument("-log",help="Redirect logs to a given file in addition to the console.",metavar='')
	parser.add_argument("-v",action='store_true',help="Enable verbose logging Sink")
	args = parser.parse_args()

	# manage logging
	debug = False
	if args.v:
		debug = True

	if args.log:
		logfile = args.log
		helper.configure_logging(debug,logfile)
	else:
		helper.configure_logging(debug)
		logging.debug("debug mode enabled")

# 1. IoT devices send data to Proxy
# (2. Proxy asks Authenticate for authentification) only some %
# 3. Proxy forwards request to Compute
# 4. a. Compute offloads into Cloud
#    b. Compute computes locally 
#    c. Compute answers with cached data 
#
#		|					*EDGE_CLOUD *					|				* PUBLIC CLOUD *
#		|					*************					|				****************
#		|		   	   #####################				|
#		|		  	  /# 5092 AUTHENTICATE #				|4.a  ######################\
# IoT--	|			2/ #####################			  --------# 5093 Cloud Compute # \
#     |	|			/									 /	|	  ######################  \
# IoT------##############				################/	|4.a  ######################   \#################
#	  1 |  # 5090 PROXY #---------------# 5091 Compute #----------# 5093 Cloud Compute #----# 5094 Database #
# IoT------##############   \   3   /	################\	|	  ######################   /#################
#		|		   		 	 -------				     \	|4.a  ######################  /
# IoT------##############   /  3    \	################  --------# 5093 Cloud Compute # /		
#	  1 |  # 5090 PROXY #---------------# 5091 COMPUTE #	|	  ######################/
# IoT------##############				################	|
#															|

	# define Interface against Proxy devices	
	edge_interface = ListenNetworkInterface(t_name="Edge_Interface",
					listen_host="0.0.0.0",
					listen_port=args.listen_port,
					maximum_number_of_listen_clients=args.max_clients,
					queque_maxsize=args.queue_size
					)
	
	# setup pipeline for cached responses
	if args.cached_percentile < 0:
		logging.error("{} Negative Percentile for cached_percentile requests(-cached_percentile).".format(t_name))
		sys.exit(1)
	if args.cached_percentile > 100:
		logging,error("{} Unable to set a Percentile greater 100. (-cached_percentile).".format(t_name))
		sys.exit(1)
	in_edge_cached_pl = queue.Queue(maxsize=args.queue_size) # maybe define helper function
	edge_interface.fork_handler.add_fork(pipeline=in_edge_cached_pl,probability=args.cached_percentile,pos=0)
	# setup pipeline for requests which require database request
	if args.database_request_percentile < 0:
		logging.error("{} Negative Percentile for database equests(-database_request_percentile).".format(t_name))
		sys.exit(1)
	if args.database_request_percentile > 100:
		logging,error("{} Unable to set a Percentile greater 100. (-cached_percentile).".format(t_name))
		sys.exit(1)
	in_edge_database_pl = queue.Queue(maxsize=args.queue_size) # maybe define helper function
	edge_interface.fork_handler.add_fork(pipeline=in_edge_database_pl,probability=args.database_request_percentile,pos=0)	

	# get pipeline for compute only requests
	__,in_edge_compute_only_pl = edge_interface.fork_handler.get_fork(-1)

	# define cloud loadbalancer 
	database_lb_host_list = []
	for c in args.database:
		database_lb_host_list.append((c,args.database_port))
	# define Interface against Authenticate devices	
	database_load_balancer = RoundRobinLoadBalancer(host_list=database_lb_host_list)
	database_interface = SendNetworkInterface(t_name="Database_Interface",
											load_balancer=database_load_balancer,
											queque_maxsize=args.queue_size)

	# get pipeline for traffic to send to edge
	out_edge_pl = edge_interface.get_after_work_pipeline()
	# get pipeline for traffic to send to database
	out_databae_pl = database_interface.get_after_work_pipeline()
	
	# forwarding shortcut
	#cloud_compute_interface.set_default_fork_pipeline(out_cloud_compute_pl)
	
	# initialize  workers
	cache_process = CacheProcess()
	for i in range(0,1):
		w = Worker(
			t_name="CacheProcess_Worker",
			incoming_pipeline=in_edge_cached_pl,
			outgoing_pipeline=out_edge_pl,
			process=cache_process)
		ELEMENTS.append(w)
		w.start()

	database_request_process = ForwardingProcess() # maybe small computation here
	for i in range(0,1):
		w = Worker(
			t_name="DatabaseRequestProcess_Worker",
			incoming_pipeline=in_edge_database_pl,
			outgoing_pipeline=out_databae_pl,
			process=database_request_process)
		ELEMENTS.append(w)
		w.start()
	
	compute_process = ComputeProcess() 
	for i in range(0,1):
		w = Worker(
			t_name="ComputeProcess_Worker",
			incoming_pipeline=in_edge_compute_only_pl,
			outgoing_pipeline=out_edge_pl,
			process=compute_process)
		ELEMENTS.append(w)
		w.start()

	database_response_process = ComputeDatabaseResponseProcess() 
	for i in range(0,1):
		w = Worker(
			t_name="ComputeDatabaseResponseProcess_Worker",
			incoming_pipeline=in_edge_compute_only_pl,
			outgoing_pipeline=out_edge_pl,
			process=compute_process)
		ELEMENTS.append(w)
		w.start()

		# start networking
	ELEMENTS.append(edge_interface)
	edge_interface.start()
	ELEMENTS.append(database_interface)
	database_interface.start()

	while RUNNING:
		edge_interface.connection_handler.clean(timeout=1)
		database_interface.connection_handler.clean(timeout=1)
		time.sleep(args.cleaning_interval)

	edge_interface.join()
	database_interface.join()
	sys.exit(0)


class CacheProcess(Process):

	def __init__(self):
		super().__init__()
		self.t_name = "CacheProcess"
		vm_bytes=1024*2000
		self.vm = VM(method="zero-one",vm_bytes=vm_bytes)
		self.children["VM"]=self.vm

	def execute(self,device_id,request_id):
		self.vm.utilize_vm()

class ComputeProcess(Process):

	def __init__(self):
		super().__init__()
		self.t_name = "ComputeProcess"
		self.cpu = CPU(method="nsqrt",max_ops=10)
		self.children["CPU"]=self.cpu

	def execute(self,device_id,request_id):
		self.cpu.utilize_cpu()

class ComputeDatabaseResponseProcess(Process):


	def __init__(self):
		super().__init__()
		self.t_name = "ComputeDatabaseResponseProcess"
		vm_bytes= 1024*8000
		self.cpu = CPU(method="nsqrt",max_ops=10)
		self.vm = VM(method="flip",vm_bytes=vm_bytes)
		self.children["CPU"]=self.cpu
		self.children["VM"]=self.cpu
		Process().__init__()

	def execute(self,device_id,request_id):
		self.cpu.utilize_cpu()
		self.vm.utilize_vm()

if __name__ == '__main__':
	main()

