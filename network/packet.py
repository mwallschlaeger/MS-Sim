import struct

from sim import MSSimObject

class WrongPayloadSizeError(Exception):
		pass

class MSSimPacket(MSSimObject):
	
	DEVICE_ID_LEN = 12
	REQUEST_ID_LEN = 16
	REQUEST_TYPE_LEN = 4
	PAYLOAD_SIZE_LEN = 8
	HEADER_LEN = DEVICE_ID_LEN + REQUEST_ID_LEN + REQUEST_TYPE_LEN + PAYLOAD_SIZE_LEN

	def __str__(self):
		return "device_id: {}, request_id: {}, request_type: {}, payload_size: {}".format(	self.header.device_id,
																							self.header.request_id,
																							self.header.request_type,
																							self.header.payload_size)

	def __init__(self,device_id : bytes,request_id : bytes,request_type : bytes ,payload_size : bytes):
		self.__set_header__(device_id=device_id,
							request_id=request_id,
							request_type=request_type,
							payload_size=payload_size)


	def __set_header__(self,device_id : bytes,request_id : bytes,request_type : bytes, payload_size : bytes ):
		self.header = MSSimHeader(	device_id=device_id,
									request_id=request_id,
									request_type=request_type,
									payload_size=payload_size)

	
	def set_payload(self,payload : bytes):
		if len(payload) == self.header.get_payload_size_int():
			self.payload = payload
		else:
			raise WrongPayloadSizeError("failed to set payload, length and content differ ....")

	# retunr integer value
	def get_payload_size(self):
		return self.header.get_payload_size_int()

class MSSimHeader():
	def __init__(self,device_id,request_id,request_type,payload_size):
		self.device_id = device_id
		self.request_id = request_id
		self.request_type = request_type
		self.payload_size = payload_size
		self.payload_size_int = struct.unpack("Q",payload_size)[0]

	def get_header(self):
		return self.device_id + self.request_id + self.request_type + payload_size


	def get_payload_size(self):
		return self.payload_size

	def get_payload_size_int(self):
		return self.payload_size_int