#!/usr/bin/python3

import argparse, time, logging, queue, sys, random, threading, signal, os
from listen_network_interface import ListenNetworkInterface
from send_network_interface import SendNetworkInterface
from process import Process, ForwardingProcess
from worker import Worker
from vm import VM
from load_balancer import RoundRobinLoadBalancer
from process import Process

RUNNING = True # controls main loop
ELEMENTS = []
t_name = "MS-AUTHENTICATE"


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

def sig_int_handler(signal, frame):
	# TODO somehow not closing everything properly

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
	
	# authentication
	parser.add_argument("-listen_port",type=int, default=5092,help="Port to listen for incoming messages")
	parser.add_argument("-max_clients",type=int,default=5000,help="maximum number of clients connected to authentication")
	parser.add_argument("-queue_size",type=int,default=5000,help="Size of interal processing queue")

	# general 
	parser.add_argument("-cleaning_interval",type=int,default=2,help="interval in which broken connections got cleared")

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
		configure_logging(debug,logfile)
	else:
		configure_logging(debug)
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

	# define Interface against IoT devices	
	proxy_interface = ListenNetworkInterface(t_name="ProxyInterface",
					listen_host="0.0.0.0",
					listen_port=args.listen_port,
					maximum_number_of_listen_clients=args.max_clients,
					queque_maxsize=args.queue_size
					)

	# get pipeline for incoming traffic
	__,in_proxy_pl = proxy_interface.get_fork(-1)
	
	# get pipeline for traffic send to proxy
	out_proxy_pl = proxy_interface.get_after_work_pipeline()
	
	# initialize all workers
	proxy_to_proxy = ProxyToProxyProcess()
	for i in range(0,2):
		w = Worker(
			in_proxy_pl,
			out_proxy_pl,
			proxy_to_proxy)
		ELEMENTS.append(w)
		w.start()

	# start networking
	ELEMENTS.append(proxy_interface)
	proxy_interface.start()

	while RUNNING:
		proxy_interface.clean(args.cleaning_interval)
		time.sleep(2)

	proxy_interface.join()
	sys.exit(0)

class ProxyToProxyProcess(Process):

	t_name = "ProxyToProxyProcess"

	def __init__(self):
		self.vm = VM(method="walk-0a",vm_bytes=1024*1000) #MB
		self.conf["authentications"] = 0
		self.children["VM"] = self.vm
		Process().__init__()

	def execute(self,device_id,request_id):
		self.conf["authentications"] += 1
		self.vm.utilize_vm() 

if __name__ == '__main__':
	main()
