"""
Home Assistant Medication Tracker integration.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import MedicationTrackerCoordinator
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

# List of platforms to support
PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Medication Tracker from a config entry."""
    # Initialize the data storage
    hass.data.setdefault(DOMAIN, {})
    
    # Create the coordinator
    coordinator = MedicationTrackerCoordinator(hass)
    await coordinator.async_setup()
    
    # Store the coordinator
    hass.data[DOMAIN]["coordinator"] = coordinator
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Set up the platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Set up services
    await async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok 