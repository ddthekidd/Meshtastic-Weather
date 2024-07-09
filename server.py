#!/usr/bin/env python3

"""
Meshtastic Weather Alerts System
Date: 07/09/2024
Version: 0.1.0

Description:
This system fetches weather alerts from the National Weather Service and
broadcasts them to a Meshtastic network.
"""

import logging
import time
import requests
from config_init import initialize_config, get_interface, init_cli_parser, merge_config
from meshtastic import BROADCAST_NUM

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_weather_alerts(state: str):
    url = f"https://api.weather.gov/alerts/active/area/{state}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json().get('features', [])

def broadcast_alerts(alerts, interface):
    for alert in alerts:
        properties = alert['properties']
        message = f"⚠️ Weather Alert: {properties['event']}\n{properties['headline']}\n{properties['description']}"
        logging.info(f"Broadcasting message: {message}")
        interface.sendText(message, BROADCAST_NUM)

def main():
    args = init_cli_parser()
    config_file = args.config if args.config else None
    system_config = initialize_config(config_file)
    merge_config(system_config, args)

    interface = get_interface(system_config)
    state = system_config['state']

    logging.info(f"Weather Alerts system running for state: {state} on {system_config['interface_type']} interface...")

    try:
        while True:
            alerts = fetch_weather_alerts(state)
            if alerts:
                broadcast_alerts(alerts, interface)
            else:
                logging.info("No active alerts at the moment.")
            time.sleep(600)  # Check every 10 minutes
    except KeyboardInterrupt:
        logging.info("Shutting down the Weather Alerts system...")
        interface.close()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        interface.close()

if __name__ == "__main__":
    main()
