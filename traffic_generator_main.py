import threading, queue, socket, time, random, logging

class Sender(threading.Thread):

	def __init__(self,host,port,id_str):
		self.port = port
		self.host = host
		self.id_str = str(id_str)
		self.running = True
		self.msg_c = 0
		super().__init__()

	def run(self):
		while self.running:
			self.msg_c+=1
			try:
				self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				self.s.connect((self.host, self.port))
			except OSError as os_error:
				logging.debug("Could not assign request addr, opponent overloaded ...")
				t = random.uniform(0.03,0.05)
				time.sleep(t)
				continue
					
			self.s.send(bytes(self.id_str, "utf-8"))
			self.s.close()
			t = random.uniform(0.03,0.05)
			time.sleep(t)

	def get_c(self):
		return self.msg_c

	def stop(self):
		logging.info("Stopping Load Generator {} ...".format(self.id_str))
		self.running = False

def main():
	
	duration = 20

	logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

	senders = []
	for i in range(0,50):
		senders.append(Sender("localhost",5090,i))

	for sender in senders:
		sender.start()

	time.sleep(duration)
	msg_c = 0
	for sender in senders:
		msg_c += sender.get_c()
		sender.stop()

	print("send {} messages in {} seconds ...".format(str(msg_c),duration))

if __name__ == '__main__':
	main()
