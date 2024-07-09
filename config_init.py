import configparser
import time
from typing import Any
import meshtastic.stream_interface
import meshtastic.serial_interface
import meshtastic.tcp_interface
import serial.tools.list_ports
import argparse
import requests

def init_cli_parser() -> argparse.Namespace:
    """Function builds the CLI parser and parses the arguments.

    Returns:
        argparse.Namespace: Argparse namespace with processed CLI args
    """
    parser = argparse.ArgumentParser(description="Meshtastic Weather Alerts System")
    
    parser.add_argument(
        "--config", "-c",
        action="store",
        help="System configuration file",
        default=None)
    
    parser.add_argument(
        "--interface-type", "-i",
        action="store",
        choices=['serial', 'tcp'],
        help="Node interface type",
        default=None)
    
    parser.add_argument(
        "--port", "-p",
        action="store",
        help="Serial port",
        default=None)
    
    parser.add_argument(
        "--host", 
        action="store",
        help="TCP host address",
        default=None)
    
    parser.add_argument(
        "--location", '-l',
        action="store",
        help="State code for weather alerts (e.g., IL for Illinois)",
        required=True)

    args = parser.parse_args()
    
    return args


def merge_config(system_config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    """Function merges configuration read from the config file and provided on the CLI.
    
    CLI arguments override values defined in the config file.
    system_config argument is mutated by the function.

    Args:
        system_config (dict[str, Any]): System config dict returned by initialize_config()
        args (argparse.Namespace): argparse namespace with parsed CLI args

    Returns:
        dict[str, Any]: system config dict with merged configurations
    """
    
    if args.interface_type is not None:
        system_config['interface_type'] = args.interface_type
        
    if args.port is not None:
        system_config['port'] = args.port
        
    if args.host is not None:
        system_config['host'] = args.host
    
    if args.location is not None:
        system_config['location'] = args.location
    
    return system_config


def initialize_config(config_file: str = None) -> dict[str, Any]:
    """
    Function reads and parses the system configuration file.

    Returns a dict with the following entries:
    config - parsed config file
    interface_type - type of the active interface
    hostname - host name for TCP interface
    port - serial port name for serial interface

    Args:
        config_file (str, optional): Path to config file. Function reads from './config.ini' if this arg is set to None. Defaults to None.

    Returns:
        dict: dict with system configuration, as described above
    """
    config = configparser.ConfigParser()

    if config_file is None:
        config_file = "config.ini"

    try:
        config.read(config_file)
    except FileNotFoundError:
        print(f"Configuration file {config_file} not found. Using default settings.")

    interface_type = config['interface'].get('type', None)
    hostname = config['interface'].get('hostname', None)
    port = config['interface'].get('port', None)

    return {
        'config': config,
        'interface_type': interface_type,
        'hostname': hostname,
        'port': port,
        'location': config.get('weather', 'location', fallback=None)
    }


def get_interface(system_config: dict[str, Any]) -> meshtastic.stream_interface.StreamInterface:
    """
    Function opens and returns an instance of meshtastic interface of type specified by the configuration
    
    Function creates and returns an instance of a class inheriting from meshtastic.stream_interface.StreamInterface.
    The type of the class depends on the type of the interface specified by the system configuration.
    For 'serial' interfaces, function returns an instance of meshtastic.serial_interface.SerialInterface,
    and for 'tcp' interface, an instance of meshtastic.tcp_interface.TCPInterface.

    Args:
        system_config (dict[str, Any]): A dict with system configuration. See description of initialize_config() for details.

    Raises:
        ValueError: Exception raised in the following cases:
                - Type of interface not provided in the system config
                - Multiple serial ports present in the system, and no port specified in the configuration
                - Serial port interface requested, but no ports found in the system
                - Hostname not provided for TCP interface

    Returns:
        meshtastic.stream_interface.StreamInterface: An instance of StreamInterface
    """
    while True:
        try:
            if system_config['interface_type'] == 'serial':
                if system_config['port']:
                    return meshtastic.serial_interface.SerialInterface(system_config['port'])
                else:
                    ports = list(serial.tools.list_ports.comports())
                    if len(ports) == 1:
                        return meshtastic.serial_interface.SerialInterface(ports[0].device)
                    elif len(ports) > 1:
                        port_list = ', '.join([p.device for p in ports])
                        raise ValueError(f"Multiple serial ports detected: {port_list}. Specify one with the 'port' argument.")
                    else:
                        raise ValueError("No serial ports detected.")
            elif system_config['interface_type'] == 'tcp':
                if not system_config['hostname']:
                    raise ValueError("Hostname must be specified for TCP interface")
                return meshtastic.tcp_interface.TCPInterface(hostname=system_config['hostname'])
            else:
                raise ValueError("Invalid interface type specified in config file")
        except PermissionError as e:
            print(f"PermissionError: {e}. Retrying in 5 seconds...")
            time.sleep(5)


def fetch_weather_alerts(location: str) -> dict:
    """
    Function fetches weather alerts from the National Weather Service API.

    Args:
        location (str): State code for which to fetch weather alerts

    Returns:
        dict: A dictionary containing weather alerts
    """
    url = f"https://api.weather.gov/alerts/active/area/{location}"
    headers = {
        'User-Agent': 'MeshtasticWeatherAlertSystem/1.0 (your_email@example.com)'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch weather alerts: {response.status_code}")
        return {}


def broadcast_weather_alerts(interface: meshtastic.stream_interface.StreamInterface, alerts: dict):
    """
    Function broadcasts weather alerts over the Meshtastic network.

    Args:
        interface (meshtastic.stream_interface.StreamInterface): Meshtastic interface to use for broadcasting
        alerts (dict): Dictionary containing weather alerts
    """
    if 'features' in alerts and alerts['features']:
        for feature in alerts['features']:
            properties = feature.get('properties', {})
            event = properties.get('event', 'Unknown Event')
            description = properties.get('description', 'No description available')
            message = f"Weather Alert: {event} - {description}"
            interface.sendText(message)
            print(f"Broadcasting: {message}")
    else:
        print("No weather alerts to broadcast.")


def main():
    args = init_cli_parser()
    config = initialize_config(args.config)
    system_config = merge_config(config, args)
    interface = get_interface(system_config)
    
    while True:
        alerts = fetch_weather_alerts(system_config['location'])
        broadcast_weather_alerts(interface, alerts)
        time.sleep(600)  # Check for new alerts every 10 minutes


if __name__ == "__main__":
    main()
