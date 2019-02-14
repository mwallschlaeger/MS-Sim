import socket, threading, logging, random, select, sys, queue,time
from network_interface import NetworkInterface
from sim import MSSimThread

class SendNetworkInterface(NetworkInterface):
	''' meta networking class'''

	def __init__(self,
				load_balancer,
				t_name=None,
				select_timeout=0.1,
				multiprocessing_worker=False,
				queue_maxsize=1000,
				put_work_task_timeout=0.05,
				pull_work_task_timeout=0.05
				):

		NetworkInterface.__init__(self,
								t_name=t_name,
								queue_maxsize=queue_maxsize,
								put_work_task_timeout=put_work_task_timeout,
								pull_work_task_timeout=pull_work_task_timeout
								)

		self.sink = Sink(t_name=t_name,
						network=self,
						load_balancer=load_balancer,
						)


		self.source = Source(t_name=t_name,
							network=self,
							select_timeout=select_timeout
							)


class Source(MSSimThread):

	def __init__(self, t_name, network, select_timeout=0.1):
		super().__init__()
		self.network = network

		self.t_name = t_name + "_Source"
		self.conf["select_timeout"] = select_timeout
		self.conf["running"] = True
		self.metrics["select_timeouts"] = 0
		self.metrics["closed_sockets_by_error"] = 0
		self.metrics["closed_sockets"] = 0
		self.metrics["encoding_error"] = 0

	def __str__(self):
		return self.t_name

	def run(self):
		while self.conf["running"]:
			try:
				read_sockets, __, error_sockets = select.select(
										self.network.connection_handler.get_all_sockets() ,
										 [],
										 [],
										 self.conf["select_timeout"])
			except ValueError as VE1:
				logging.debug("{}: overloaded ...".format(self.t_name))

				self.metrics["select_timeouts"] += 1
				continue
			except KeyError as KE1:
				pass # runtime dynamic dict error in connection handlelr

			for sock in read_sockets:
				# receive and process data
				try:
					data = sock.recv(self.network.conf["recv_bytes"])
				except InterruptedError as IE1:
					logging.debug("{}: could not recv data properly. Closing socket ...".format(self.t_name))
					#logging.debug("{}".format(str(IE1)))
					self.metrics["closed_sockets_by_error"] += 1
					sock.close()
					continue
				except OSError:
					logging.debug("{}: could not recv data properly. Closing socket ...".format(self.t_name))
					self.metrics["closed_sockets_by_error"] += 1
					# BAD FILE DESCRIPTOR
					sock.close()
				except ConnectionResetError as CRE1:
					logging.debug("{}: connection reset by peer ...".format(self.t_name))
					self.metrics["closed_sockets_by_error"] += 1
					sock.close()
					continue
				packet = self.network.read_msg(data)
				if packet is None:
					self.metrics["encoding_error"] += 1
					self.metrics["closed_sockets_by_error"] += 1
					logging.debug("{}: could not parse received msg properly ...".format(self.t_name))
					sock.close()
					continue

				self.metrics["closed_sockets"] += 1
				sock.close()
				if self.network.put_work_task(packet):
					self.network.connection_handler.delete_connection(request_id=packet.header.request_id)

	def stop(self):
		self.conf["running"] = False
		logging.debug("{}: stopping  ...".format(str(self)))


''' sending packets to other hosts '''
class Sink(MSSimThread):

	def __init__(self, t_name, network, load_balancer):
		super().__init__()
		self.network = network 
		self.load_balancer = load_balancer

		self.t_name = t_name + "_Sink"
		self.children["load_balancer"] = load_balancer
		self.conf["running"] = True
		self.metrics["reading_on_empty_queue"] = 0
		self.metrics["no_lb_endpoint_error"] = 0
		self.metrics["connection_timeouts"] = 0

	def __str__(self):
		return self.t_name

	def run(self):
		logging.debug("{}: initialized ...".format(str(self)))
		while self.conf["running"]:
			try:
				packet = self.network.pull_work_result()
			except queue.Empty as E1:
				self.metrics["reading_on_empty_queue"] += 1
				continue

			msg = self.network.build_msg(packet)
			address = self.load_balancer.get_next_endpoint()
			if address is None:
				self.metrics["no_lb_endpoint_error"] += 1
				logging.debug("{}: No loadbalancer endpoint defined, unable to send messages ...".format(self.t_name))
				continue
			try:
				send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				send_socket.connect(address)
			except ConnectionRefusedError as CRE1:
				self.metrics["connection_timeouts"] += 1
				logging.debug("{}: connection timeout ...".format(self.t_name))
				send_socket.close()
				self.network.pull_task_done()
				continue
			except socket.gaierror:
				logging.debug("{}: hostname error ...".format(self.t_name))
				send_socket.close()
				self.network.pull_task_done()
				continue

			try:	
				send_socket.send(msg)
			except: 
				send_socket.close()
				self.metrics["closed_sockets_by_error"] += 1
				logging.warning("{}: sending message failed  ...".format(self.t_name))
				continue

			self.network.connection_handler.add_connection(	socket=send_socket,
															address=address,
															packet=packet)

	def stop(self):
		self.conf["running"] = False
		logging.debug("{}: stopping  ...".format(str(self)))