import threading, queue, socket, time, random, logging


duration = 30
worker = 100

class IoTDevice(threading.Thread):

	def __init__(self,host,port,device_id):
		self.port = port
		self.host = host
		self.device_id = device_id # bytes
		self.running = True

		self.bytes_out = 0
		self.bytes_in = 0
		self.msg_out = 0
		self.msg_in = 0

		padding_len =  random.randint(2545,25555)
		self.padding =  random_string(padding_len)
		super().__init__()

	def run(self):
		while self.running:
			try:
				self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				self.s.connect((self.host, self.port))
			except OSError as os_error:
				logging.debug("Could not assign request addr, opponent overloaded ...")
				t = random.uniform(0.03,0.05)
				time.sleep(t)
				continue
			msg = self.build_msg()
			self.bytes_out += len(msg)
			self.msg_out+=1
			self.s.send(msg)
			logging.debug("send msg: {} ...".format(msg))

			# use poll  here to implement timeout function
			response_msg = self.s.recv(4096)
			logging.debug("received msg: {}".format(msg))
			self.msg_in+=1
			self.bytes_in += len(response_msg)

			self.s.close()
			t = random.uniform(0.9,1)
			time.sleep(t)

	def get_padding(self):
		return self.padding

	def build_msg(self):
		request_id = random_string(16)
		padding = self.get_padding()
		return bytes(self.device_id + request_id + padding,"utf-8")
		#return bytes(self.device_id + request_id,"utf-8")

	def get_send_msg(self):
		return self.msg_out

	def get_recv_msg(self):
		return self.msg_in

	def get_send_bytes(self):
		return self.msg_out

	def get_recv_bytes(self):
		return self.bytes_in

	def stop(self):
		logging.info("Stopping Load Generator {} ...".format(self.device_id))
		self.running = False


# https://stackoverflow.com/questions/976577/random-hash-in-python ported to p3
def random_string(length):
	import string
	pool = string.ascii_lowercase + string.digits
	return ''.join(random.choice(pool) for i in range(length))

def main():
	global duration
	global worker

	logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

	senders = []
	for i in range(0,worker):
		senders.append(IoTDevice(
							"localhost",
							5090,
							random_string(12)
							))

	for sender in senders:
		sender.start()

	input("Press Enter to stop ...")
	#time.sleep(duration)
	msg_send = 0
	msg_recv = 0
	bytes_send = 0
	bytes_recv = 0 
	for sender in senders:
		msg_send += sender.get_send_msg()
		msg_recv += sender.get_recv_msg()

		bytes_send += sender.get_send_bytes()
		bytes_recv += sender.get_recv_bytes()

		sender.stop()

	print("send messages: " + str(msg_send) + "  \n \
		   received messeges: " + str(msg_recv) + " \n \
		   overall MBytes send: " + str(bytes_send / 1000 / 1000) + " \n \
		   overall MBytes recv: " + str(bytes_recv / 1000 / 1000) + " \n \
   		   avg MBits/s out: " + str(bytes_send / 1000 / 1000 / 8 / duration) + " \n \
		   avg MBits/s in: " + str(bytes_recv / 1000 / 1000 / 8 / duration) + " \n \
		   benchmark duration: " + str(duration))

if __name__ == '__main__':
	main()
