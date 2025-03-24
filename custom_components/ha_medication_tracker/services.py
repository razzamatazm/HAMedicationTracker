"""Services for the Medication Tracker integration."""
from __future__ import annotations

import logging
from datetime import datetime
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    SERVICE_ADD_PATIENT,
    SERVICE_REMOVE_PATIENT,
    SERVICE_ADD_MEDICATION,
    SERVICE_REMOVE_MEDICATION,
    SERVICE_RECORD_DOSE,
    SERVICE_RECORD_TEMPERATURE,
    ATTR_PATIENT_ID,
    ATTR_PATIENT_NAME,
    ATTR_PATIENT_WEIGHT,
    ATTR_PATIENT_WEIGHT_UNIT,
    ATTR_PATIENT_AGE,
    ATTR_MEDICATION_ID,
    ATTR_MEDICATION_NAME,
    ATTR_MEDICATION_DOSAGE,
    ATTR_MEDICATION_UNIT,
    ATTR_MEDICATION_FREQUENCY,
    ATTR_MEDICATION_MAX_DAILY_DOSES,
    ATTR_MEDICATION_INSTRUCTIONS,
    ATTR_DOSE_TIMESTAMP,
    ATTR_DOSE_AMOUNT,
    ATTR_DOSE_UNIT,
    ATTR_TEMPERATURE_TIMESTAMP,
    ATTR_TEMPERATURE_VALUE,
    ATTR_TEMPERATURE_UNIT,
)
from .coordinator import MedicationTrackerCoordinator

_LOGGER = logging.getLogger(__name__)

# Service schema for adding a patient
ADD_PATIENT_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_PATIENT_ID): cv.string,
        vol.Required(ATTR_PATIENT_NAME): cv.string,
        vol.Optional(ATTR_PATIENT_WEIGHT): vol.Coerce(float),
        vol.Optional(ATTR_PATIENT_WEIGHT_UNIT, default="kg"): cv.string,
        vol.Optional(ATTR_PATIENT_AGE): vol.Coerce(int),
    }
)

# Service schema for removing a patient
REMOVE_PATIENT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PATIENT_ID): cv.string,
    }
)

# Service schema for adding a medication
ADD_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_MEDICATION_ID): cv.string,
        vol.Required(ATTR_PATIENT_ID): cv.string,
        vol.Required(ATTR_MEDICATION_NAME): cv.string,
        vol.Optional(ATTR_MEDICATION_DOSAGE): vol.Coerce(float),
        vol.Optional(ATTR_MEDICATION_UNIT, default="mg"): cv.string,
        vol.Optional(ATTR_MEDICATION_FREQUENCY, default=6): vol.Coerce(float),  # Hours
        vol.Optional(ATTR_MEDICATION_MAX_DAILY_DOSES): vol.Coerce(int),
        vol.Optional(ATTR_MEDICATION_INSTRUCTIONS): cv.string,
    }
)

# Service schema for removing a medication
REMOVE_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    }
)

# Service schema for recording a dose
RECORD_DOSE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_ID): str,
        vol.Optional(ATTR_DOSE_TIMESTAMP, default=lambda: datetime.now().isoformat()): str,
        vol.Optional(ATTR_DOSE_AMOUNT): vol.Coerce(float),
        vol.Optional(ATTR_DOSE_UNIT): str,
    }
)

# Service schema for recording a temperature
RECORD_TEMPERATURE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PATIENT_ID): str,
        vol.Required(ATTR_TEMPERATURE_VALUE): vol.Coerce(float),
        vol.Optional(ATTR_TEMPERATURE_TIMESTAMP, default=lambda: datetime.now().isoformat()): str,
        vol.Optional(ATTR_TEMPERATURE_UNIT, default="°C"): str,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up the Medication Tracker services."""
    
    # Get the coordinator
    coordinator = hass.data[DOMAIN].get("coordinator")
    if not coordinator:
        _LOGGER.error("Cannot set up services - coordinator not found")
        return
        
    async def async_handle_add_patient(call: ServiceCall) -> None:
        """Handle the add_patient service call."""
        patient_data = {
            "id": call.data.get(ATTR_PATIENT_ID),
            "name": call.data.get(ATTR_PATIENT_NAME),
            "weight": call.data.get(ATTR_PATIENT_WEIGHT),
            "weight_unit": call.data.get(ATTR_PATIENT_WEIGHT_UNIT),
            "age": call.data.get(ATTR_PATIENT_AGE),
        }
        
        patient_id = await coordinator.add_patient(patient_data)
        _LOGGER.info("Added patient %s with ID %s", patient_data["name"], patient_id)
        
    async def async_handle_remove_patient(call: ServiceCall) -> None:
        """Handle the remove_patient service call."""
        patient_id = call.data.get(ATTR_PATIENT_ID)
        result = await coordinator.remove_patient(patient_id)
        
        if result:
            _LOGGER.info("Removed patient with ID %s", patient_id)
        else:
            _LOGGER.warning("Failed to remove patient with ID %s - not found", patient_id)
        
    async def async_handle_add_medication(call: ServiceCall) -> None:
        """Handle the add_medication service call."""
        medication_data = {
            "id": call.data.get(ATTR_MEDICATION_ID),
            "patient_id": call.data.get(ATTR_PATIENT_ID),
            "name": call.data.get(ATTR_MEDICATION_NAME),
            "dosage": call.data.get(ATTR_MEDICATION_DOSAGE),
            "unit": call.data.get(ATTR_MEDICATION_UNIT),
            "frequency": call.data.get(ATTR_MEDICATION_FREQUENCY),
            "max_daily_doses": call.data.get(ATTR_MEDICATION_MAX_DAILY_DOSES),
            "instructions": call.data.get(ATTR_MEDICATION_INSTRUCTIONS),
        }
        
        medication_id = await coordinator.add_medication(medication_data)
        _LOGGER.info("Added medication %s with ID %s", medication_data["name"], medication_id)
        
    async def async_handle_remove_medication(call: ServiceCall) -> None:
        """Handle the remove_medication service call."""
        medication_id = call.data.get(ATTR_MEDICATION_ID)
        result = await coordinator.remove_medication(medication_id)
        
        if result:
            _LOGGER.info("Removed medication with ID %s", medication_id)
        else:
            _LOGGER.warning("Failed to remove medication with ID %s - not found", medication_id)
        
    async def async_handle_record_dose(call: ServiceCall) -> None:
        """Handle the record_dose service call."""
        medication_id = call.data.get(ATTR_MEDICATION_ID)
        
        dose_data = {
            "timestamp": call.data.get(ATTR_DOSE_TIMESTAMP),
            "amount": call.data.get(ATTR_DOSE_AMOUNT),
            "unit": call.data.get(ATTR_DOSE_UNIT),
        }
        
        # Convert datetime object to ISO string if provided
        if isinstance(dose_data["timestamp"], datetime):
            dose_data["timestamp"] = dose_data["timestamp"].isoformat()
            
        result = await coordinator.record_dose(medication_id, dose_data)
        
        if result:
            _LOGGER.info("Recorded dose for medication ID %s", medication_id)
        else:
            _LOGGER.warning("Failed to record dose for medication ID %s - not found", medication_id)
        
    async def async_handle_record_temperature(call: ServiceCall) -> None:
        """Handle the record_temperature service call."""
        patient_id = call.data.get(ATTR_PATIENT_ID)
        
        temperature_data = {
            "timestamp": call.data.get(ATTR_TEMPERATURE_TIMESTAMP),
            "value": call.data.get(ATTR_TEMPERATURE_VALUE),
            "unit": call.data.get(ATTR_TEMPERATURE_UNIT),
        }
        
        # Convert datetime object to ISO string if provided
        if isinstance(temperature_data["timestamp"], datetime):
            temperature_data["timestamp"] = temperature_data["timestamp"].isoformat()
            
        result = await coordinator.record_temperature(patient_id, temperature_data)
        
        if result:
            _LOGGER.info("Recorded temperature for patient ID %s", patient_id)
        else:
            _LOGGER.warning("Failed to record temperature for patient ID %s - not found", patient_id)
    
    # Register services
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_PATIENT, async_handle_add_patient, schema=ADD_PATIENT_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_PATIENT, async_handle_remove_patient, schema=REMOVE_PATIENT_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_MEDICATION, async_handle_add_medication, schema=ADD_MEDICATION_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_MEDICATION, async_handle_remove_medication, schema=REMOVE_MEDICATION_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_RECORD_DOSE, async_handle_record_dose, schema=RECORD_DOSE_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_RECORD_TEMPERATURE, async_handle_record_temperature, schema=RECORD_TEMPERATURE_SCHEMA
    ) 