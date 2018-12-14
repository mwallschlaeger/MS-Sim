#!/usr/bin/python3

import argparse, time, logging, queue, sys, random, threading, signal, os
from listen_network_interface import ListenNetworkInterface
from send_network_interface import SendNetworkInterface
from worker import Worker
from load_balancer import RoundRobinLoadBalancer
from process import Process, ForwardingProcess

RUNNING = True # controls main loop
ELEMENTS = []
t_name = "MS-PROXY"

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
	global __t_name
	signal.signal(signal.SIGINT, sig_int_handler)

	parser = argparse.ArgumentParser()
	
	# proxy
	parser.add_argument("-listen_port",type=int, default=5090,help="Port to listen for incoming messages")
	parser.add_argument("-authenticate",action='append',help="a Compute node to interact with",required=True)
	parser.add_argument("-authenticate_port",type=int,default=5092,help="Port the compute nodes are listening on")
	parser.add_argument("-authentication_percentile",type=int,default=10,help="a Compute node to interact with")
	parser.add_argument("-compute",action='append',help="a Compute node to interact with",required=True)
	parser.add_argument("-compute_port",type=int,default=5091,help="Port the compute nodes are listening on")
	parser.add_argument("-max_clients",type=int,default=5000,help="maximum number of clients connected to proxy")
	parser.add_argument("-queue_size",type=int,default=5000,help="Size of interal processing queue")

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
	iot_interface = ListenNetworkInterface(t_name="IoT_Device_Interface",
					listen_host="0.0.0.0",
					listen_port=args.listen_port,
					maximum_number_of_listen_clients=args.max_clients,
					queque_maxsize=args.queue_size)	
	# setup pipeline to authentication, for 10% of all request comming from IoT devices
	if args.authentication_percentile < 0:
		logging.error("{} Negative Percentile for Authentication requests(-authentication_percentile).".format(t_name))
		sys.exit(1)
	if args.authentication_percentile > 100:
		logging,error("{} Unable to set a Percentile greater 100. (-authentication_percentile).".format(t_name))
		sys.exit(1)
	iot_interface.add_fork(pipeline=in_iot_out_authentication_pl,probability=args.authentication_percentile,pos=0)
	in_iot_out_authentication_pl = queue.Queue(maxsize=args.queue_size) # maybe define helper function
	# get pipeline for incoming traffic from IoT devices
	__,in_iot_out_compute_pl = iot_interface.get_fork(-1)

	# define authenticate loadbalancer 
	authenticate_lb_host_list = []
	for c in args.authenticate:
		authenticate_lb_host_list.append((c,args.authenticate_port))
	# define Interface against Authenticate devices	
	authenticate_load_balancer = RoundRobinLoadBalancer(host_list=authenticate_lb_host_list)
	authentication_interface = SendNetworkInterface(t_name="Authenticate_Interface",
											load_balancer=authenticate_load_balancer,
											queque_maxsize=args.queue_size)
	# get pipeline for incoming traffic from authentication
	__,in_authentication_out_compute_pl = authentication_interface.get_fork(-1)

	# define compute loadbalancer 
	compute_lb_host_list = []
	for c in args.compute:
		compute_lb_host_list.append((c,args.compute_port))
	compute_load_balancer = RoundRobinLoadBalancer(host_list=compute_lb_host_list)
	# define Interface against Compute nodes
	compute_interface = SendNetworkInterface(t_name="Compute_Interface",
											load_balancer=compute_load_balancer,
											queque_maxsize=args.queue_size)
	# get pipeline for incoming traffic from compute
	__,in_compute_out_iot_pl = authentication_interface.get_fork(-1)
	
	
	# get pipeline for traffic to send to IoT devices
	out_iot_pl = iot_interface.get_after_work_pipeline()
	# get pipeline for traffic to send to authenticate
	out_authentication_pl = authentication_interface.get_after_work_pipeline()
	# get pipeline for traffic to send to Compute instances
	out_compute_pl = compute_interface.get_after_work_pipeline()

	# initialize  workers
	proxy_to_authentication = ForwardingProcess("ProxyToAuthenticationProcess")
	for i in range(0,1):
		w = Worker(
			in_iot_out_authentication_pl,
			out_authentication_pl,
			proxy_to_authentication)
		ELEMENTS.append(w)
		w.start()
	
	authentication_to_compute = ForwardingProcess("AuthenticationToProxyProcess")
	for i in range(0,1):
		w = Worker(
			in_authentication_out_compute_pl,
			out_authentication_pl,
			authentication_to_compute)
		ELEMENTS.append(w)
		w.start()

	proxy_to_comp = ForwardingProcess("ProxyToComputeProcess")
	for i in range(0,1):
		w = Worker(
			in_iot_out_compute_pl,
			out_compute_pl,
			proxy_to_comp
			)
		ELEMENTS.append(w)
		w.start()

	comp_to_proxy = ForwardingProcess("ComputeToProxyProcess")
	for i in range(0,1):
		w = Worker(
			in_compute_out_iot_pl,
			out_iot_pl,
			comp_to_proxy
			)
		ELEMENTS.append(w)
		w.start()

	# start networking
	ELEMENTS.append(iot_interface)
	iot_interface.start()
	ELEMENTS.append(authentication_interface)
	authentication_interface.start()
	ELEMENTS.append(compute_interface)
	compute_interface.start()

	while RUNNING:
		iot_interface.clean(timeout=1)
		authentication_interface.clean(timeout=1)
		compute_interface.clean(timeout=1)
		time.sleep(args.cleaning_interval)

	iot_interface.join()
	authentication_interface.join()
	compute_interface.join()

	sys.exit(0)

if __name__ == '__main__':
	main()

