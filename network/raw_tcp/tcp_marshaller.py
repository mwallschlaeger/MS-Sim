from network.packet import MSSimPacket

def check_data_size(data,required_size):
	if len(data) >= required_size:
		return True
	return False

def unmarshall(data):
	if check_data_size(data,MSSimPacket.HEADER_LEN):
		packet = unmarshall_header(data)
	else:
		return data, None
	
	if check_data_size(data,packet.get_payload_size()):
		data = unmarshall_payload(data,packet)
	else:
		return data, None
	return data,packet

def unmarshall_header(data):
	offset = 0
	device_id = data[offset:MSSimPacket.DEVICE_ID_LEN]
	offset  += MSSimPacket.DEVICE_ID_LEN
	request_id = data[offset:offset+MSSimPacket.REQUEST_ID_LEN]
	offset += MSSimPacket.REQUEST_ID_LEN
	request_type = data[offset:offset+MSSimPacket.REQUEST_TYPE_LEN]
	offset += MSSimPacket.REQUEST_TYPE_LEN
	payload_size = data[offset:offset+MSSimPacket.PAYLOAD_SIZE_LEN]
	packet = MSSimPacket(device_id,request_id,request_type,payload_size)
	return packet

def unmarshall_payload(data,packet):
	offset = MSSimPacket.HEADER_LEN
	payload_size = packet.get_payload_size()
	payload = data[offset:payload_size]
	packet.set_payload(payload)
	return data[offset + payload_size:len(data)]

def marshall(packet):
	return packet.header.device_id + packet.header.request_id + packet.header.request_type + packet.header.payload_size + packet.payload
