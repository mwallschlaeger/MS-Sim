
class MSSimPacket():
	conf = {}
	conf["device_id_len"] = 12
	conf["request_id_len"] = 16
	conf["request_type_len"] = 4

	def __init__(self,data):
		
		device_id = data[0:MSSimPacket.conf["device_id_len"]]
		request_id = data[self.conf["device_id_len"]:self.conf["device_id_len"]+self.conf["request_id_len"]]
		request_type = data[self.conf["device_id_len"]+self.conf["request_id_len"]:self.conf["device_id_len"]+self.conf["request_id_len"]+self.conf["request_type_len"]]

		self.header = MSSimHeader(device_id=device_id,
							request_id=request_id,
							request_type=request_type
							)
		self.payload = b''

	def get_message(self):
		msg = self.header.get_header() + self.payload
		return msg

class MSSimHeader():
	def __init__(self,device_id,request_id,request_type):
		self.device_id = device_id
		self.request_id = request_id
		self.request_type = request_type

	def get_header(self):
		return self.device_id + self.request_id + self.request_type