# RabbitMQ Simple Queue Alerter
Simple python script to send pagerduty alerts on queues getting above a threshold size.

## Usage
The code needs to be run as a cronjob running per minute or as per the requirement.
$python rabbitmq_alerter.py

##Features
1. Override default threshold size for specific queues.
2. Auto resolve pagerduty incident if the queue get backs to normal.
3. Do not page for the same queue if it is already being reported once and the incidence is still open.

## Config file
The config file contains all the server config for rabbitMQ and pagerduty.

In addition to that it can contain any queue name and expected max size before alerting. If the queue name is not specified it would take the default threshold.


