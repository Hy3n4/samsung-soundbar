"""Platform for Samsung Soundbar integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Optional
from urllib.parse import quote, urlencode

import aiohttp
from homeassistant.components.media_player import (
    PLATFORM_SCHEMA,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
import voluptuous as vol
import xmltodict

from .const import DEFAULT_PORT

_LOGGER = logging.getLogger(__name__)

# Define constants for your integration
DOMAIN = "samsung_soundbar"
DEFAULT_NAME = "Samsung Soundbar"
TIMEOUT = 10
VOLUME_STEP = 1

SCAN_INTERVAL = timedelta(seconds=5)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST, default="127.0.0.1"): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Samsung Soundbar platform."""
    # Discovery info is typically provided by the platform's configuration.

    host = config[CONF_HOST]
    port = config[CONF_PORT]

    add_entities([SamsungSoundbarEntity(hass, config[CONF_NAME], host, port)], True)


class SoundbarAPI:
    """Representation of Samsung Soundbar."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        """Initialize the SoundbarAPI object with the necessary details for API communication.

        :param hass: An instance of HomeAssistant, which allows access to Home Assistant's internal functionality,
                    such as creating an HTTP session.
        :param host: The IP address or hostname of the soundbar to communicate with.
        :param port: The port number on which the soundbar's API server is running.
        """
        self.endpoint = f"http://{host}:{port}/UIC"
        self.session = async_get_clientsession(hass)

    async def exec_cmd(
        self, cmd: str, key_to_extract: str, endpoint: Optional[str] = None
    ):
        """Asynchronously execute a command against the soundbar's API endpoint and extract a specified value.

        The function sends a command to the soundbar over HTTP within a specified timeout period,
        parses the XML response, and then returns the value associated with 'key_to_extract'.

        :param session: An instance of aiohttp.ClientSession for making HTTP requests.
        :param endpoint: The full URL (including port if necessary) to the soundbar's API endpoint.
        :param cmd: The command string, specific to the soundbar's protocol, to be sent to the endpoint.
        :param key_to_extract: The key that will be used to extract the desired piece of information from
                            the parsed XML response.
        :return: The value from the parsed response associated with 'key_to_extract', or None if the key
                is not found in the response.
        :raises: aiohttp.ClientError if the HTTP request fails.
        :raises: asyncio.TimeoutError if the request times out based on the specified timeout value.
        """
        endpoint = endpoint or self.endpoint

        query = urlencode({"cmd": cmd}, quote_via=quote)
        url = f"{endpoint}?{query}"

        timeout_obj = aiohttp.ClientTimeout(total=TIMEOUT)

        try:
            async with self.session.get(url, timeout=timeout_obj) as response:
                _LOGGER.debug("Executing: %s with cmd: %s", url, cmd)
                response.raise_for_status()  # Raises an aiohttp.ClientError if the http status is 400 or higher
                data = await response.text()
                _LOGGER.debug(data)
                response_dict = xmltodict.parse(data)
                return response_dict["UIC"]["response"].get(key_to_extract)
        except aiohttp.ClientError as e:
            _LOGGER.error("HTTP request to %s failed: %s", url, e)
            raise  # Rethrow the exception to handle it further up the chain
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout when executing command: %s", cmd)
            raise  # Rethrow the exception to handle it further up the chain

    async def get_value(self, action: str, key_to_extract: str):
        """Asynchronously send a command to the soundbar to get a specific value.

        :param action: The action name corresponding to the API call for the soundbar.
        :param key_to_extract: The key (parameter) to extract from the API response.
        :return: Returns the value extracted from the XML response for the specified key.
        """
        cmd = f"<name>{action}</name>"
        return await self.exec_cmd(cmd, key_to_extract)

    async def set_value(self, action: str, property_name: str, value):
        """Asynchronously send a command to the soundbar to set a specific value.

        :param action: The action name corresponding to the API call for the soundbar.
        :param property_name: The name of the property to set on the soundbar.
        :param value: The value to set for the given property,
                      appropriately for matted as a string or decimal as required by the API.
        :return: Returns the response from the API after attempting to set the value.
        """
        value_type = "str" if isinstance(value, str) else "dec"
        cmd = f'<name>{action}</name><p type="{value_type}" name="{property_name}" val="{value}"/>'
        return await self.exec_cmd(cmd, property_name)

    async def get_soundbar_status(self):
        """Asynchronously retrieve the current status of various soundbar parameters.

        This function makes a series of API calls to get the current state of the soundbar,
        such as its power state, volume level and mute status. Each API call may need to be
        customized to fit the specific implementation requirements of the soundbar.

        :return: Returns a dictionary object containing key status parameters of the soundbar.
        """
        status = {}
        status["power"] = await self.get_value("<name>GetPowerStatus</name>", "power")
        status["volume"] = await self.get_value("<name>GetVolume</name>", "volume")
        status["mute"] = await self.get_value("<name>GetMute</name>", "mute")

        return status


class SamsungSoundbarEntity(MediaPlayerEntity):
    """Representation of a Samsung Soundbar entity."""

    _attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )

    def __init__(self, hass: HomeAssistant, name, host, port) -> None:
        """Initialize the Samsung Soundbar entity."""
        _LOGGER.info("Initializing Samsung Soundbar")
        self._name = name
        self._host = host
        self._volume = None
        self._state = MediaPlayerState.OFF
        self._is_muted = False
        self._api = SoundbarAPI(hass, host, port)

    @property
    def name(self) -> None:
        """Return the name of the device."""
        return self._name

    @property
    def state(self) -> None:
        """Return the state of the device."""
        return self._state

    @property
    def volume_level(self) -> None:
        """Return the volume level of the device (0..1)."""
        return self._volume

    @property
    def is_on(self):
        """Return True if the device is on."""
        return self._state == STATE_ON

    @property
    def is_volume_muted(self) -> None:
        """Boolean if volume is currently muted."""
        return self._is_muted

    async def async_update(self) -> None:
        """Fetch the latest state from the device."""
        status = await self._api.get_soundbar_status()
        self._is_muted = status["mute"] == "on"
        self._volume = float(status["volume"]) / 100  # Assuming volume is out of 100

        if status["power"] == "off":
            self._state = STATE_OFF
        else:
            # Add additional logic to determine if the state should be STATE_IDLE or another value
            # For example:
            # if status['playing']:
            #     self._state = STATE_PLAYING
            # else:
            self._state = STATE_ON  # or STATE_ON if appropriate

    async def async_mute_volume(self, mute: bool) -> None:
        """Send the mute toggle command."""
        mute_value = "on" if mute else "off"
        await self._api.set_value("SetMute", "mute", mute_value)

    async def async_set_volume_level(self, volume: float) -> None:
        """Convert the volume from a 0.0-1.0 scale to a 0-100 scale."""
        volume_level = int(volume * 100)
        await self._api.set_value("SetVolume", "volume", volume_level)
