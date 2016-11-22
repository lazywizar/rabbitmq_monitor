import subprocess
import ConfigParser
import json
import requests

config = ConfigParser.ConfigParser()
config.read('./rabbit_monitor.conf')

host = config.get('server', 'host')
port = config.get('server', 'port')
rabbitadminpath = config.get('server', 'rabbit_admin_path')
username = config.get('server', 'username')
password = config.get('server', 'password')
threshold = config.getint('server', 'threshold')

API_ACCESS_KEY = config.get('pagerduty', 'api_access_key')
service_key = config.get('pagerduty', 'service_key')

def run_command(command):
    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         shell=True)

    # Read stdout from subprocess until the buffer is empty !
    for line in iter(p.stdout.readline, b''):
        if line: 
            yield line
    # Wait for the return command
    while p.poll() is None:                                                                                                                                        
        sleep(.1) 
    err = p.stderr.read()
    if p.returncode != 0:
       # The run_command() function is responsible for logging STDERR 
       print "Error: " + err 

def get_queues_with_size():
    command = rabbitadminpath + " --host=" + host + " --port=" + port + " --username=" + username + " --password=" + password + " list queues"
    queues_size = {}
    for line in run_command(command):
        tokens = line.split("|")

        if len(tokens) == 4 and tokens[2].replace(" ", "") != 'messages':
            queues_size[tokens[1].replace (" ", "")] = int(tokens[2].replace(" ", ""))
    return queues_size

def get_alert_queues():
    alert_queues = {}
    alert_queues_str = ""
    queues_size = get_queues_with_size()
    for queue, size in queues_size.iteritems():
        queue_threshold = threshold
        if config.has_option('queues', queue):
            queue_threshold = config.getint('queues', queue)

        if size > queue_threshold:
            alert_queues[queue] = size
            alert_queues_str = alert_queues_str + queue + " - " + str(size) + "\n"
    return alert_queues

def trigger_incident(description):
    headers = {
        'Authorization': 'Token token={0}'.format(API_ACCESS_KEY),
        'Content-type': 'application/json',
    }
    payload = json.dumps({
      "service_key": service_key,
      "event_type": "trigger",
      "description": "Rabbit queues backlogged : " + description,
      "client": "Rabbit Alert",
      "client_url": "https://monitoring.service.com",
      "details": {
        "ping time": "1500ms",
        "load avg": 0.75
      }
    })
    r = requests.post(
                    'https://events.pagerduty.com/generic/2010-04-15/create_event.json',
                    headers=headers,
                    data=payload,
    )
    print r.status_code
    print r.text

if __name__ == '__main__':
	alert_queues = get_alert_queues()

	if bool(alert_queues):
		trigger_incident(json.dumps(alert_queues))
