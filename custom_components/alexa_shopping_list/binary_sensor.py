#!/usr/bin/env python3

import logging
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup binary sensors from a config entry created in the integrations UI."""
    alexa = hass.data[DOMAIN][config_entry.entry_id]
    auth_sensor = AlexaShoppingListAuthSensor(hass, alexa)
    async_add_entities([auth_sensor], update_before_add=True)


class AlexaShoppingListAuthSensor(BinarySensorEntity):
    """Binary sensor representing authentication status."""

    def __init__(self, hass, alexa):
        self.hass = hass
        self.alexa = alexa

        self._attr_name = "Alexa Shopping List Authenticated"
        self._attr_unique_id = "alexa_shopping_list_authenticated"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self):
        """Return true if the server is authenticated."""
        return self.alexa.is_authenticated

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        await self.alexa.get_server_auth_cached_state()
