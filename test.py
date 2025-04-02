import ahttp
import json

def test_get(http, ip, varid, notif):
	try:
		url = f"http://{ip}/v.api/apis/EV/GET/parameter/{varid}"
		op = http.get(url, block=True)
		op_content = json.loads(op.content)
		value = op_content.get("value", None)
		print(f"{notif}: {value}")
	except:
		raise Exception(f"Cannot connect to {ip}. ")

def test_set(http, ip, varid, value):
	try:
		url = f"http://{ip}/v.api/apis/EV/SET/parameter/{varid}/{value}"
		op = http.get(url, block=True)
	except:
		raise Exception(f"Cannot connect to {ip}. ")

IP = '172.16.199.10'
NOTIFICATIONS = {
	"CPU Usage too high": "850.2@i",
	"CPU Temperature too high": "850.3@i",
	"Memory Usage too high": "850.4@i",
	"FPGA temperature fabric too high": "850.5@i",
	"FPGA temperature BR too high": "850.6@i",
	"FPGA temperature TR too high": "850.7@i",
	"FPGA temperature BL too high": "850.8@i",
	"FPGA temperature TL too high": "850.9@i",
	"NTP Error": "850.18@i",
	"CPU Load too high": "850.19@i",
	"NTP Unsynchronised": "850.20@i",
	"SSD Critical Warning": "850.21@i",
	"High lifetime disk usage": "850.23@i",
	"Genlock REF 1 Missing": "850.24@i",
	"Genlock REF 2 Missing": "850.25@i",
	"Serial FVH 1 Missing": "850.26@i",
	"Serial FVH 2 Missing": "850.27@i"
}

http = ahttp.start()
for notification, varid in NOTIFICATIONS.items():
	test_get(http, IP, varid, notification)
test_set(http, IP, "850.27@i", "0")