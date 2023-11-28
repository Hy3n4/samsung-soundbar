from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .const import DOMAIN

DEFAULT_PORT = 80


class SoundbarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Soundbar."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # Verify the configuration. If it fails, show the form again with an error message.
            ip_address = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            if await self._test_connection(ip_address, port):
                return self.async_create_entry(title="Soundbar", data=user_input)
            else:
                errors["base"] = "cannot_connect"

        # Show initial configuration form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
            }),
            errors=errors,
        )

    async def _test_connection(self, ip_address, port):
        """Test if we can connect to the soundbar."""
        # Here you would use the IP and port to try to make a request
        # to the soundbar and return True if successful.
        session = async_get_clientsession(self.hass)
        try:
            # You would use your existing method, e.g., `self.exec_cmd()`,
            # to send a test command to the soundbar and check the response.
            # This example is just a placeholder and won't actually work.
            response = await session.get(f"http://{ip_address}:{port}/test")
            response.raise_for_status()
            return True
        except Exception:
            return False


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for Soundbar."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options for the custom component."""
        # Here you can add options for your soundbar integration,
        # like adjusting volume control settings, updating login credentials, etc.
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_HOST, default=self.config_entry.data.get(CONF_HOST)): str,
                vol.Optional(CONF_PORT, default=self.config_entry.data.get(CONF_PORT, DEFAULT_PORT)): vol.Coerce(int),
            }),
        )
