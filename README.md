# RabbitMQ Simple Queue Alerter
Simple python script to send pagerduty alerts on queues getting above a threshold size.

## Usage
$python rabbitmq_alerter.py

## Config file
The config file contains all the server config for rabbitMQ. In addition to that it can contain any queue name and expected max size before alerting. If the queue name is not specified it would take the default threshold.

