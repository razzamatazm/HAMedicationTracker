"""
Home Assistant Medication Tracker integration.
"""
from __future__ import annotations

import logging
from typing import Any
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

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
    coordinator = MedicationTrackerCoordinator(hass, entry)
    await coordinator.async_setup()
    
    # Store coordinator in hass data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["coordinator"] = coordinator
    
    # Register services
    async def record_dose_service(call):
        """Handle record dose service call."""
        medication_id = call.data.get("medication_id")
        dose_data = {
            "amount": call.data.get("amount"),
            "unit": call.data.get("unit"),
            "notes": call.data.get("notes", ""),
            "timestamp": call.data.get("timestamp", datetime.now().isoformat())
        }
        await coordinator.record_dose(medication_id, dose_data)
        
    hass.services.async_register(
        DOMAIN, 
        "record_dose", 
        record_dose_service, 
        schema=vol.Schema({
            vol.Required("medication_id"): cv.string,
            vol.Optional("amount"): vol.Coerce(float),
            vol.Optional("unit"): cv.string,
            vol.Optional("notes"): cv.string,
            vol.Optional("timestamp"): cv.datetime,
        })
    )
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


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