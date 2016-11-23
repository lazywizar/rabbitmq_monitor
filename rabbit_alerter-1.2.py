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

#Pageduty confs
API_ACCESS_KEY = config.get('pagerduty', 'api_access_key')
SERVICE_KEY = config.get('pagerduty', 'service_key')
SERVICE_ID = config.get('pagerduty', 'service_id') 
SERVICE_IDS = [SERVICE_ID]

PREFIX_ERROR_MESSAGE = "Rabbit queue backlogged : "
STATUSES = ['triggered']

EMAIL = "varun.kumar@experticity.com"
SUMMARY = 'Queue got drained'
RESOLVED = 'resolved'
TYPE = 'incident'

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
    queues_size = get_queues_with_size()
    for queue, size in queues_size.iteritems():
        queue_threshold = threshold
        if config.has_option('queues', queue):
            queue_threshold = config.getint('queues', queue)

        if size > queue_threshold:
            alert_queues[queue] = size
    return alert_queues

def monitor():
    alert_queues = get_alert_queues()
    print "Queues above threshold: " + str(alert_queues)

    existing_tickets = get_open_incidents()
    print "Existing incidences : " + str(existing_tickets)

    new_queues = {}
    incidents_to_be_resolved = []

    #Find the ones which are no longer in danger.. resolve them!
    print "Getting queues which got auto resolved"
    if bool(existing_tickets):
        for queue, incident_id in existing_tickets.iteritems():
            if queue not in alert_queues:
                incidents_to_be_resolved.append(incident_id)
        
        print "Queues auto resolved: " + str(incidents_to_be_resolved)
        if bool(incidents_to_be_resolved):
            resolve_incidents(incidents_to_be_resolved)
    else:
        print "\tNone"

    #Find the new ones for which we have not yet sent tickets
    print "Getting queues which are above threshold and needs new alert"
    if bool(alert_queues):
        for queue, size in alert_queues.iteritems():
            if queue not in existing_tickets:
                new_queues[queue] = size

        print "Raising incidents for : " + str(new_queues)
        if bool(new_queues):
            trigger_incidents(new_queues)
    else:
        print "\tNone"

#Pageduty stuff
def trigger_incidents(alert_queues):
    for queue, size in alert_queues.iteritems():
        description =  PREFIX_ERROR_MESSAGE + queue + " : " + str(size)
        trigger_incident(description)

def trigger_incident(description):
    headers = {
        'Authorization': 'Token token={0}'.format(API_ACCESS_KEY),
        'Content-type': 'application/json',
    }
    payload = json.dumps({
      "service_key": SERVICE_KEY,
      "event_type": "trigger",
      "description": description,
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


def get_open_incidents():
    url = 'https://api.pagerduty.com/incidents'
    headers = {
        'Accept': 'application/vnd.pagerduty+json;version=2',
        'Authorization': 'Token token={token}'.format(token=API_ACCESS_KEY)
    }
    payload = {
        'statuses[]': STATUSES,
        'service_ids[]': SERVICE_IDS,
    }
    print 'Getting status'
    r = requests.get(url, headers=headers, params=payload)
    print 'Status Code: {code}'.format(code=r.status_code)
    status_response = json.loads(r.text)
    existing_tickets = {}
    for incident in status_response["incidents"]:
        #incident = json.loads(key)
        description = incident['description'] 
        if PREFIX_ERROR_MESSAGE in description:
            incident_id = incident['id']
            toks = description.split(":")
            queue_name  = toks[1].replace(" ", "")
            print queue_name + " - " + incident_id
            existing_tickets[queue_name] = incident_id
    return existing_tickets

def resolve_incidents(incidents_to_be_resolved):
    for incident_id in incidents_to_be_resolved:
        resolve_incident(incident_id)

def resolve_incident(incident_id):
    url = 'https://api.pagerduty.com/incidents/{id}'.format(id=incident_id)
    headers = {
        'Accept': 'application/vnd.pagerduty+json;version=2',
        'Authorization': 'Token token={token}'.format(token=API_ACCESS_KEY),
        'Content-type': 'application/json',
        'From': EMAIL
    }
    payload = {
        'incident': {
            'summary': SUMMARY,
            'status': RESOLVED,
            'type' : TYPE
        }
    }
    r = requests.put(url, headers=headers, data=json.dumps(payload))
    print 'Status Code: {code}'.format(code=r.status_code)
    print r.json()

if __name__ == '__main__':
    monitor()

