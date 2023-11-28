from homeassistant import core


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Samsung Soundbar from a config entry."""
    # TODO Optionally store an object for your platforms to access
    # hass.data.setdefault(DOMAIN, {})[entry.entry_id] = ...

    # TODO Optionally validate config entry options before setting up platform

    await hass.config_entries.async_forward_entry_setups(entry, (Platform.SENSOR,))

    # TODO Remove if the integration does not have an options flow
    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))

    return True
