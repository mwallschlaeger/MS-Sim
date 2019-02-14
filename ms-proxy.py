#!/usr/bin/env python

import argparse, time, logging, queue, sys, random, threading, signal, os
from listen_network_interface import ListenNetworkInterface
from send_network_interface import SendNetworkInterface
from thread_worker import ThreadWorker
from load_balancer import RoundRobinLoadBalancer
from process import *
import helper

RUNNING = True # controls main loop
ELEMENTS = []
t_name = "MS-PROXY"

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
	global __t_name
	signal.signal(signal.SIGINT, sig_int_handler)

	parser = argparse.ArgumentParser()
	
	# proxy
	parser.add_argument("-listen_port",type=int, default=5090,help="Port to listen for incoming messages")
	parser.add_argument("-authentication",action='append',help="a Compute node to interact with",required=True)
	parser.add_argument("-authentication_port",type=int,default=5092,help="Port the compute nodes are listening on")
	parser.add_argument("-authentication_percentile",type=int,default=10,help="a Compute node to interact with")
	parser.add_argument("-compute",action='append',help="a Compute node to interact with",required=True)
	parser.add_argument("-compute_port",type=int,default=5091,help="Port the compute nodes are listening on")
	parser.add_argument("-optimized",action='store_true',help="run with reduced amount of threads and pipes")
	parser.add_argument("-max_clients",type=int,default=5000,help="maximum number of clients connected to proxy")
	parser.add_argument("-queue_size",type=int,default=5000,help="Size of interal processing queue")

	# general 
	parser.add_argument("-cleaning_interval",type=int,default=2,help="interval in which broken connections got cleared",metavar='2')
	# Multiprocessing not implemented yet, due to conflicts with -optimized

	# logging
	parser.add_argument("-log",help="Redirect service quality data to a given file.",metavar='')
	parser.add_argument("-status_log",help="Redirect logs to a given file in addition to the console.",metavar='')
	parser.add_argument("-v",action='store_true',help="Enable verbose logging Sink")
	args = parser.parse_args()

	# manage logging
	debug = False
	if args.v:
		debug = True

	if args.status_log:
		logfile = args.status_log
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
	
	# setup pipeline to authentication, for 10% of all request comming from IoT devices
	if args.authentication_percentile < 0:
		logging.error("{} Negative Percentile for Authentication requests(-authentication_percentile).".format(t_name))
		sys.exit(1)
	if args.authentication_percentile > 100:
		logging.error("{} Unable to set a Percentile greater 100. (-authentication_percentile).".format(t_name))
		sys.exit(1)
	to_compute_percentile = 100 - args.authentication_percentile

	# define Interface against IoT devices	
	iot_interface = ListenNetworkInterface(t_name="IoT_Device_Interface",
					listen_host="0.0.0.0",
					listen_port=args.listen_port,
					maximum_number_of_listen_clients=args.max_clients,
					queue_maxsize=args.queue_size)	
	
	# define compute loadbalancer 
	compute_lb_host_list = []
	for c in args.compute:
		compute_lb_host_list.append((c,args.compute_port))
	compute_load_balancer = RoundRobinLoadBalancer(host_list=compute_lb_host_list)
	# define Interface against Compute nodes
	compute_interface = SendNetworkInterface(t_name="Compute_Interface",
											load_balancer=compute_load_balancer,
											queue_maxsize=args.queue_size)

	# define authenticate loadbalancer 
	authenticate_lb_host_list = []
	for c in args.authentication:
		authenticate_lb_host_list.append((c,args.authentication_port))
	# define Interface against Authenticate devices	
	authenticate_load_balancer = RoundRobinLoadBalancer(host_list=authenticate_lb_host_list)
	authentication_interface = SendNetworkInterface(t_name="Authenticate_Interface",
											load_balancer=authenticate_load_balancer,
											queue_maxsize=args.queue_size)
		

	# OLDSCHOOL COOL
	if not args.optimized:
		# pipeline from iot to authentication
		in_authentication_pl = helper.get_queue(multiprocessing_worker=False,maxsize=args.queue_size)
		iot_interface.fork_handler.add_fork(pipeline=in_authentication_pl,probability=args.authentication_percentile)
		
		# pipeline from iot to compute
		in_compute_pl = helper.get_queue(multiprocessing_worker=False,maxsize=args.queue_size)
		iot_interface.fork_handler.add_fork(pipeline=in_compute_pl,probability=to_compute_percentile)


		# pipeline from authenticate to compute
		in_authenticate_compute_pl = helper.get_queue(multiprocessing_worker=False,maxsize=args.queue_size)
		authentication_interface.fork_handler.add_fork(pipeline=in_authenticate_compute_pl,probability=100)

		# pipeline from compute to iot
		in_compute_iot_pl = helper.get_queue(multiprocessing_worker=False,maxsize=args.queue_size)
		compute_interface.fork_handler.add_fork(pipeline=in_compute_iot_pl,probability=100)

		
		
		# get pipeline for traffic to send to IoT devices
		out_iot_pl = iot_interface.get_send_pipeline()
		# get pipeline for traffic to send to authenticate
		out_authentication_pl = authentication_interface.get_send_pipeline()
		# get pipeline for traffic to send to Compute instances
		out_compute_pl = compute_interface.get_send_pipeline()

		# initialize  workers
		proxy_to_authentication = Forwarding()
		for i in range(0,1):
			w = helper.spawn_worker(
				t_name="ProxyToAuthenticationProcess_Worker",
				incoming_pipeline=in_authentication_pl,
				outgoing_pipeline=out_authentication_pl,
				default_process=proxy_to_authentication
				)
			ELEMENTS.append(w)
			w.start()
		
		authentication_to_compute = Forwarding()
		for i in range(0,1):
			w = helper.spawn_worker(
				t_name="AuthenticationToProxyProcess_Worker",
				incoming_pipeline=in_authenticate_compute_pl,
				outgoing_pipeline=out_authentication_pl,
				default_process=authentication_to_compute
				)
			ELEMENTS.append(w)
			w.start()

		proxy_to_comp = Forwarding()
		for i in range(0,1):
			w = helper.spawn_worker(
				t_name="ProxyToComputeProcess_Worker",
				incoming_pipeline=in_compute_pl,
				outgoing_pipeline=out_compute_pl,
				default_process=proxy_to_comp
				)
			ELEMENTS.append(w)
			w.start()

		comp_to_proxy = Forwarding()
		for i in range(0,1):
			w = helper.spawn_worker(
				t_name="ComputeToProxyProcess_Worker",
				incoming_pipeline=in_compute_iot_pl,
				outgoing_pipeline=out_iot_pl,
				default_process=comp_to_proxy
				)
			ELEMENTS.append(w)
			w.start()

	# OPTIMIZED WAY
	else: 
		
		# get pipeline for traffic to send to authenticate
		out_authentication_pl = authentication_interface.get_send_pipeline()
		# get pipeline for traffic to send to IoT devices
		out_iot_pl = iot_interface.get_send_pipeline()
		# get pipeline for traffic to send to Compute instances
		out_compute_pl = compute_interface.get_send_pipeline()

		iot_interface.fork_handler.add_fork(pipeline=out_authentication_pl,probability=args.authentication_percentile)
		# set default pipeline for incoming traffic from IoT devices to send to compute 
		iot_interface.fork_handler.add_fork(pipeline=out_compute_pl,probability=to_compute_percentile)
		# set default pipeline for incoming traffic from Authentication service to send to compute 
		authentication_interface.fork_handler.add_fork(pipeline=out_compute_pl,probability=100)
		compute_interface.fork_handler.add_fork(pipeline=out_iot_pl,probability=100)


	# start networking
	ELEMENTS.append(iot_interface)
	iot_interface.start()
	ELEMENTS.append(authentication_interface)
	authentication_interface.start()
	ELEMENTS.append(compute_interface)
	compute_interface.start()

	file_obj = None
	if args.log:
		pass
	#	file_obj = open(args.log,"w")
	#helper.log_metrics([authentication_interface,iot_interface,compute_interface,proxy_to_authentication,authentication_to_compute,proxy_to_comp,comp_to_proxy],print_header=True,file_obj=file_obj)

	while RUNNING:
		iot_interface.connection_handler.clean(timeout=1)
		authentication_interface.connection_handler.clean(timeout=1)
		compute_interface.connection_handler.clean(timeout=1)
		#helper.log_metrics([authentication_interface,iot_interface,compute_interface,proxy_to_authentication,authentication_to_compute,proxy_to_comp,comp_to_proxy],file_obj=file_obj)
		time.sleep(args.cleaning_interval)

	if args.log:
		pass
		#file_obj.close()

	iot_interface.join()
	authentication_interface.join()
	compute_interface.join()

	sys.exit(0)

if __name__ == '__main__':
	main()

