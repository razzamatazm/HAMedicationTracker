"""
Home Assistant Medication Tracker integration.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import MedicationTrackerCoordinator
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

# List of platforms to support
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON, Platform.SWITCH]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Medication Tracker component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Medication Tracker from a config entry."""
    try:
        # Create coordinator
        coordinator = MedicationTrackerCoordinator(hass, entry)
        await coordinator.async_setup()
        
        # Store coordinator reference with a consistent key
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN]["coordinator"] = coordinator
        
        # Set up platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        # Set up services
        await async_setup_services(hass)
        
        return True
        
    except Exception as err:
        _LOGGER.exception("Failed to set up Medication Tracker: %s", err)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        # Get coordinator
        coordinator = hass.data[DOMAIN]["coordinator"]
        
        # Save data before unloading
        await coordinator.async_shutdown()
        
        # Unload platforms
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        
        if unload_ok:
            hass.data[DOMAIN].pop("coordinator")
            
        return unload_ok
        
    except Exception as err:
        _LOGGER.exception("Error unloading Medication Tracker: %s", err)
        return False 