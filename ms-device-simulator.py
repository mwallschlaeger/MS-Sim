#!/usr/bin/env python

import threading 
import time
import logging
import signal
import argparse
import os
import sys
import struct

import helper
from network.packet import MSSimPacket
from network.load_balancer import RoundRobinLoadBalancer
from network.raw_tcp.tcp_send_interface import SendNetworkInterface

RUNNING = True # controls main loop
ELEMENTS = []

class IoTDevice(threading.Thread):
	def __init__(self,
				peers,
				network_protocol=helper.TCP_NETWORK_PROTOCOL,
				min_payload=2048,
				max_payload=4096,
				interval=1.0):

		self.device_id = os.urandom(12)
		self.interval = interval
		logging.info("initialize IoTDevice_{}".format(self.device_id))
		self.network_protocol = network_protocol
		self.running = True
		self.interface = self.initialize_interface(peers=peers)
		self.receive_q = helper.get_queue(multiprocessing_worker=False,maxsize=500)
		self.interface.fork_handler.add_fork(pipeline=self.receive_q,probability=100)
		self.send_q = self.interface.get_send_pipeline()

		self.reset_report()
		super().__init__()

	def initialize_interface(self,peers,queue_maxsize=50):
		load_balancer = RoundRobinLoadBalancer(host_list=peers)
		if self.network_protocol == helper.TCP_NETWORK_PROTOCOL:
			interface = SendNetworkInterface(t_name="IoTDevice_{}_Interface".format(self.device_id),
											 load_balancer=load_balancer,
											 queue_maxsize=queue_maxsize)
		else:
			raise NotImplementedError("Only {} networking is implemented currently".format(AVAILABLE_NETWORK_TYPES)) 
			sys.exit(1)
		interface.start()
		return interface

	def build_packet(self,request_type,payload_size):
		if self.network_protocol == helper.TCP_NETWORK_PROTOCOL:
			import network.raw_tcp.tcp_marshaller as marshaller
		else:
			raise(NotImplementedError("Unknown network protocol ..."))
		
		# payload size currently ignored
		payload = b''
		request_id = os.urandom(MSSimPacket.REQUEST_ID_LEN)
		request_type_bytes = struct.pack("i",request_type)
		payload_size = struct.pack("Q",len(payload))
		packet = MSSimPacket( 	device_id=self.device_id,
								request_id=request_id,
								request_type=request_type_bytes,
								payload_size=payload_size)
		packet.set_payload(payload=payload)
		return packet

	def wait_to_send(self,last_t):
		if last_t == 0:
			last_t = time.time()
			return last_t
		now_t = time.time()
		print(now_t,last_t,self.interval)
		sleep_time = abs(now_t - (last_t + self.interval))
		time.sleep(sleep_time)
		return last_t

	def run(self):
		last_t = 0
		while self.running:
			while not self.receive_q.empty():
				recv_packet = self.receive_q.get()
				logging.debug("{}: received packet: {} ...".format(str(self),recv_packet))
				self.msg_in+=1
				self.receive_q.task_done()

			time.sleep(self.interval)

			send_packet = self.build_packet(request_type=0,payload_size=0)
			self.msg_out += 1
			logging.debug("{}:packet put to send: {} ...".format(str(self),send_packet))
			self.send_q.put(send_packet)

	def stop(self):
		logging.debug("{}: stopping device ...".format(str(self)))
		self.interface.stop()
		self.running = False

	# reporting
	def reset_report(self):
		self.msg_out = 0
		self.msg_in = 0

	def get_send_msg(self):
		return self.msg_out

	def get_recv_msg(self):
		return self.msg_in

def print_report(devices,duration):
	msg_send = 0
	msg_recv = 0
	bytes_send = 0
	bytes_recv = 0 
	bad_socket = 0
	timeouts = 0
	for device in devices:
		msg_send += device.get_send_msg()
		msg_recv += device.get_recv_msg()

		device.reset_report()
	logging.info("send msg: " + str(msg_send) + \
		   ", recv msg: " + str(msg_recv))


def sig_int_handler(signal, frame):
	global RUNNING
	global ELEMENTS

	if RUNNING == False:
		os.kill(signal.CTRL_C_EVENT, 0)
		
	RUNNING = False
	for e in ELEMENTS:
		e.stop()

def main():
	global RUNNING
	global ELEMENTS
	report_interval = 1

	signal.signal(signal.SIGINT, sig_int_handler)
	parser = argparse.ArgumentParser()
	# load generator
	parser.add_argument("-host",action='append',help="a node to interact with (hostname:port)",metavar="example-proxy-host.com",required=True)
	parser.add_argument("-devices",type=int,default=500,metavar=50,help="Number of IoTDevices to Simulate")

	parser.add_argument("-duration",type=int, default=-1,metavar=-1,help="durations in seconds to run (-1 = forever)")
	parser.add_argument("-min_payload",default=2048,type=int,metavar=2048,help="minimum request padding size (bytes)")
	parser.add_argument("-max_payload",default=4096,type=int,metavar=4096,help="maximum request padding size (bytes)")
	parser.add_argument("-interval",default=1.0,type=float,metavar=1.0,help="sending interval")
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

	peers = []
	for h in args.host:
		try:
			host,port = h.split(":")
			port = int(port)
		except:
			logging.error("Could not parse host parameter correct, requrires \'hostname:port\'...")
			sys.exit(1)
		peers.append((host,port))
		print(peers)
	# initiate and start IoT-Devices
	iot_devices = []
	for i in range(args.devices):
		iot_device = IoTDevice(
				peers=peers,
				min_payload=args.min_payload,
				max_payload=args.max_payload,
				interval=args.interval
				)
		iot_devices.append(iot_device)
		ELEMENTS.append(iot_device)
		iot_device.start()

	if args.duration == -1:
		while(RUNNING):
			time.sleep(report_interval)
			print_report(iot_devices,report_interval)
	else:
		time.sleep(args.duration)	
		print_report(iot_devices,args.duration)
	RUNNING = False

if __name__ == '__main__':
	main()
