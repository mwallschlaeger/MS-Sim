#!/usr/bin/python3

import threading, queue, socket, time, random, logging, signal, argparse, os, sys
from load_balancer import RoundRobinLoadBalancer

RUNNING = True # controls main loop
ELEMENTS = []

class IoTDevice(threading.Thread):

	def __init__(self,
				load_balancer,
				device_id,
				min_padding=2048,
				max_padding=4096,
				interval=1.0,
				empty_queue_timeout=0.08):

		# Check if no loadbalancer
		if load_balancer is None:
			logging.error("No Load Balancer defined ...")
			# TODO 
			global RUNNING
			RUNNING = False
			sys.exit(1)
		self.load_balancer= load_balancer
		self.device_id = device_id 

		self.interval = interval
		self.empty_queue_timeout = empty_queue_timeout

		padding_len =  random.randint(min_padding,max_padding)
		self.padding =  random_string(padding_len)

		self.reset_report()
		self.running = True
		super().__init__()

	def __str__(self):
		return "IoTDevice_"+self.device_id

	def reset_report(self):
		self.bytes_out = 0
		self.bytes_in = 0
		self.msg_out = 0
		self.msg_in = 0
		self.bad_socket = 0
		self.timeouts = 0

	def wait_to_send(self):
		t = random.uniform(self.interval - (self.interval /10),self.interval + (self.interval / 10))
		time.sleep(t)

	def run(self):
		while self.running:
			try:
				self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				self.s.connect(self.load_balancer.get_next_endpoint())
				self.s.settimeout(2)
			except OSError as os_error:
				logging.debug("{}: Could not assign request addr, proxy overloaded ...".format(str(self)))
				time.sleep(self.empty_queue_timeout)
				continue
			msg = self.build_msg()
			self.bytes_out += len(msg)
			self.msg_out+=1
			try:
				self.s.send(msg)
			except ConnectionResetError:
				self.bad_socket += 1
				continue

			logging.debug("{}: send msg: ...".format(str(self)))

			# use poll  here to implement timeout function
			try:
				response_msg = self.s.recv(4096)
			except socket.timeout:
				self.timeouts += 1
				self.s.close()
				self.wait_to_send()
				continue
			except ConnectionResetError as CRE1:
				self.s.close()
				self.bad_socket += 1
				self.wait_to_send()
				continue

			logging.debug("{}: received msg ...".format(str(self)))
			self.msg_in+=1
			self.bytes_in += len(response_msg)
			self.wait_to_send()
			self.s.close()

	def get_padding(self):
		return self.padding

	def build_msg(self):
		request_id = random_string(16)
		padding = self.get_padding()
		return bytes(self.device_id + request_id + padding,"utf-8")

	def stop(self):
		logging.debug("{}: stopping device ...".format(str(self)))
		self.running = False

	# reporting
	def get_send_msg(self):
		return self.msg_out

	def get_recv_msg(self):
		return self.msg_in

	def get_send_bytes(self):
		return self.msg_out

	def get_recv_bytes(self):
		return self.bytes_in

	def get_bad_socket(self):
		return self.bad_socket

	def get_timeouts(self):
		return self.timeouts

# https://stackoverflow.com/questions/976577/random-hash-in-python ported to p3
def random_string(length):
	import string
	pool = string.ascii_lowercase + string.digits
	return ''.join(random.choice(pool) for i in range(length))

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
		bad_socket += device.get_bad_socket()
		timeouts += device.get_timeouts()
		bytes_send += device.get_send_bytes()
		bytes_recv += device.get_recv_bytes()

		device.reset_report()
	logging.info("send msg: " + str(msg_send) + \
		   ", recv msg: " + str(msg_recv) + \
		   ", bad_sock: " + str(bad_socket) + \
		   ", timeouts: " + str(timeouts) + \
		   ", MBytes send: " + str(round(bytes_send / 1000,5)) + \
		   ", MBytes recv: " + str(round(bytes_recv / 1000 ,5)) + \
		   ", MBits/s out: " + str(round(bytes_send / 1000 / duration,5)) + \
		   ", MBits/s in: " + str(round(bytes_recv / 1000 / duration,5)))
		

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
	parser.add_argument("-proxy",action='append',help="a proxy node to interact with",metavar="example-proxy-host.com",required=True)
	parser.add_argument("-proxy_port",type=int,default=5090,metavar=5090,help="Port the compute nodes are listening on")
	parser.add_argument("-devices",type=int,default=500,metavar=500,help="Number of IoTDevices to Simulate")

	parser.add_argument("-duration",type=int, default=-1,metavar=-1,help="durations in seconds to run (-1 = forever)")
	parser.add_argument("-min_padding",default=2048,type=int,metavar=2048,help="minimum request padding size (bytes)")
	parser.add_argument("-max_padding",default=4096,type=int,metavar=4096,help="maximum request padding size (bytes)")
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
		configure_logging(debug,logfile)
	else:
		configure_logging(debug)
		logging.debug("debug mode enabled")
	logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

	# define loadbalancer 
	lb_host_list = []
	for c in args.proxy:
		lb_host_list.append((c,args.proxy_port))
	round_robin_load_balancer = RoundRobinLoadBalancer(host_list=lb_host_list)

	# initiate and start IoT-Devices
	iot_devices = []
	for i in range(0,args.devices):
		iot_device = IoTDevice(
				load_balancer=round_robin_load_balancer,
				device_id=random_string(12),
				min_padding=args.min_padding,
				max_padding=args.max_padding,
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
	sys.exit(0)

if __name__ == '__main__':
	main()
