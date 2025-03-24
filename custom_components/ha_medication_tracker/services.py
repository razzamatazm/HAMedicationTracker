"""Services for the Medication Tracker integration."""
import logging
from typing import Any, Dict, List, Optional, cast

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, ATTR_MEDICATION_NAME, ATTR_MEDICATION_DOSAGE, ATTR_MEDICATION_UNIT
from .coordinator import MedicationTrackerCoordinator

_LOGGER = logging.getLogger(__name__)

# Service schemas
RECORD_DOSE_SCHEMA = vol.Schema({
    vol.Required("medication_id"): cv.string,
    vol.Optional("amount"): vol.Coerce(float),
    vol.Optional("unit"): cv.string,
    vol.Optional("notes"): cv.string,
})

TOGGLE_MEDICATION_SCHEMA = vol.Schema({
    vol.Required("medication_id"): cv.string,
    vol.Required("enabled"): cv.boolean,
})

ADD_MEDICATION_SCHEMA = vol.Schema({
    vol.Required("patient_id"): cv.string,
    vol.Required(ATTR_MEDICATION_NAME): cv.string,
    vol.Required(ATTR_MEDICATION_DOSAGE): vol.Coerce(float),
    vol.Required(ATTR_MEDICATION_UNIT): cv.string,
    vol.Required("frequency"): vol.Coerce(float),
    vol.Optional("instructions"): cv.string,
    vol.Optional("temporary"): cv.boolean,
})

UPDATE_MEDICATION_SCHEMA = vol.Schema({
    vol.Required("medication_id"): cv.string,
    vol.Optional(ATTR_MEDICATION_NAME): cv.string,
    vol.Optional(ATTR_MEDICATION_DOSAGE): vol.Coerce(float),
    vol.Optional(ATTR_MEDICATION_UNIT): cv.string,
    vol.Optional("frequency"): vol.Coerce(float),
    vol.Optional("instructions"): cv.string,
    vol.Optional("temporary"): cv.boolean,
    vol.Optional("disabled"): cv.boolean,
})

DELETE_MEDICATION_SCHEMA = vol.Schema({
    vol.Required("medication_id"): cv.string,
})

async def async_setup_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up services for the Medication Tracker integration."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    async def handle_record_dose(call: ServiceCall) -> None:
        """Handle the record_dose service call."""
        medication_id = call.data["medication_id"]
        amount = call.data.get("amount")
        unit = call.data.get("unit")
        notes = call.data.get("notes")
        
        dose_data = {}
        if amount is not None:
            dose_data["amount"] = amount
        if unit is not None:
            dose_data["unit"] = unit
        if notes is not None:
            dose_data["notes"] = notes
            
        success = await coordinator.record_dose(medication_id, dose_data)
        if not success:
            _LOGGER.error("Failed to record dose for medication %s", medication_id)
            
    async def handle_toggle_medication(call: ServiceCall) -> None:
        """Handle the toggle_medication service call."""
        medication_id = call.data["medication_id"]
        enabled = call.data["enabled"]
        
        success = await coordinator.toggle_medication_status(medication_id, enabled)
        if not success:
            _LOGGER.error("Failed to toggle medication %s to %s", medication_id, "enabled" if enabled else "disabled")
            
    async def handle_add_medication(call: ServiceCall) -> None:
        """Handle the add_medication service call."""
        patient_id = call.data["patient_id"]
        name = call.data[ATTR_MEDICATION_NAME]
        dosage = call.data[ATTR_MEDICATION_DOSAGE]
        unit = call.data[ATTR_MEDICATION_UNIT]
        frequency = call.data["frequency"]
        instructions = call.data.get("instructions", "")
        temporary = call.data.get("temporary", False)
        
        medication_data = {
            "patient_id": patient_id,
            ATTR_MEDICATION_NAME: name,
            ATTR_MEDICATION_DOSAGE: dosage,
            ATTR_MEDICATION_UNIT: unit,
            "frequency": frequency,
            "instructions": instructions,
            "temporary": temporary,
            "disabled": False,
        }
        
        medication_id = await coordinator.add_medication(medication_data)
        if not medication_id:
            _LOGGER.error("Failed to add medication %s for patient %s", name, patient_id)
            
    async def handle_update_medication(call: ServiceCall) -> None:
        """Handle the update_medication service call."""
        medication_id = call.data["medication_id"]
        
        # Get current medication data
        medications = coordinator.data.get("medications", {})
        if medication_id not in medications:
            _LOGGER.error("Medication %s not found", medication_id)
            return
            
        medication_data = dict(medications[medication_id])
        
        # Update with new values
        for key in call.data:
            if key != "medication_id":
                medication_data[key] = call.data[key]
                
        success = await coordinator.update_medication(medication_id, medication_data)
        if not success:
            _LOGGER.error("Failed to update medication %s", medication_id)
            
    async def handle_delete_medication(call: ServiceCall) -> None:
        """Handle the delete_medication service call."""
        medication_id = call.data["medication_id"]
        
        success = await coordinator.delete_medication(medication_id)
        if not success:
            _LOGGER.error("Failed to delete medication %s", medication_id)
    
    # Register services
    hass.services.async_register(
        DOMAIN, "record_dose", handle_record_dose, schema=RECORD_DOSE_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, "toggle_medication", handle_toggle_medication, schema=TOGGLE_MEDICATION_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, "add_medication", handle_add_medication, schema=ADD_MEDICATION_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, "update_medication", handle_update_medication, schema=UPDATE_MEDICATION_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, "delete_medication", handle_delete_medication, schema=DELETE_MEDICATION_SCHEMA
    )

async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Medication Tracker services."""
    for service_name in [
        "record_dose", 
        "toggle_medication", 
        "add_medication", 
        "update_medication", 
        "delete_medication"
    ]:
        hass.services.async_remove(DOMAIN, service_name) 