import logging
import requests
import time
from meshtastic import BROADCAST_NUM
from meshtastic.stream_interface import StreamInterface
from utils import send_message

WEATHER_API_URL = "https://api.weather.gov/alerts/active/area/{STATE}"

def fetch_weather_alerts(state):
    url = WEATHER_API_URL.format(STATE=state)
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('features', [])
    else:
        logging.error(f"Failed to fetch weather alerts: {response.status_code} {response.text}")
        return []

def format_alert_message(alert):
    properties = alert.get('properties', {})
    headline = properties.get('headline', 'No headline')
    description = properties.get('description', 'No description')
    instruction = properties.get('instruction', 'No instruction')

    message = f"🚨Weather Alert🚨\nHeadline: {headline}\nDescription: {description}\nInstruction: {instruction}"
    return message

def broadcast_weather_alerts(interface: StreamInterface, state: str):
    alerts = fetch_weather_alerts(state)
    for alert in alerts:
        message = format_alert_message(alert)
        send_message(message, BROADCAST_NUM, interface)

def on_receive(packet, interface):
    try:
        if 'decoded' in packet and packet['decoded']['portnum'] == 'TEXT_MESSAGE_APP':
            message_bytes = packet['decoded']['payload']
            message_string = message_bytes.decode('utf-8')
            sender_id = packet['from']
            sender_node_id = packet['fromId']

            sender_short_name = get_node_short_name(sender_node_id, interface)
            logging.info(f"Received message from '{sender_short_name}': {message_string}")

            # No special handling of received messages in this weather alert system.
            # If needed, you could add specific commands for users to trigger weather alert broadcasts.

    except KeyError as e:
        logging.error(f"Error processing packet: {e}")

# Main loop to periodically fetch and broadcast weather alerts
def main(interface: StreamInterface, state: str, interval: int = 300):
    while True:
        try:
            broadcast_weather_alerts(interface, state)
            time.sleep(interval)
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
