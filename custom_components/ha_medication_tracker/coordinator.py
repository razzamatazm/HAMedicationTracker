"""Medication Tracker Coordinator for handling data."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN
from .storage import MedicationStorage

_LOGGER = logging.getLogger(__name__)


class MedicationTrackerCoordinator(DataUpdateCoordinator):
    """Medication Tracker coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),  # Update more frequently
        )
        
        # Store the config entry
        self.config_entry = entry
        
        # Initialize storage
        self.storage = MedicationStorage(hass)
        
    async def async_setup(self) -> None:
        """Load storage data and initial config."""
        # Load storage
        await self.storage.async_load()
        
        # Initialize with config entry data if storage is empty
        if not self.storage.get_patients():
            entry_data = self.config_entry.data
            _LOGGER.debug("Initializing storage with config entry data: %s", entry_data)
            
            # Add patients
            for patient in entry_data.get("patients", []):
                self.storage.add_patient(patient)
            
            # Add medications
            for med_id, medication in entry_data.get("medications", {}).items():
                self.storage.add_medication(medication)
            
            # Save the initialized data
            await self.storage.async_save()
        
        _LOGGER.debug("Storage loaded, performing initial refresh")
        await self.async_refresh()

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data."""
        try:
            # Get all data from storage
            patients = self.storage.get_patients()
            _LOGGER.debug("Retrieved patients from storage: %s", patients)
            
            medications = self.storage.get_medications()
            doses = self.storage.get_doses()
            temperatures = self.storage.get_temperatures()
            
            # Calculate next doses
            next_doses = self._calculate_next_doses(medications, doses)
            
            # Process data and calculate next doses
            data = {
                "patients": patients,
                "medications": medications,
                "doses": doses,
                "temperatures": temperatures,
                "next_doses": next_doses,
            }
            return data
        except Exception as err:
            _LOGGER.exception("Error updating Medication Tracker data: %s", err)
            raise UpdateFailed(f"Error updating data: {err}")

    def _calculate_next_doses(self, medications: Dict[str, Any], doses: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Calculate next available dose for each medication."""
        next_doses = {}
        now = datetime.now()
        
        for medication_id, medication in medications.items():
            # Skip disabled medications
            if medication.get("disabled", False):
                next_doses[medication_id] = {
                    "available_now": False,
                    "next_time": None,
                    "last_dose_time": None,
                    "last_dose_amount": None,
                    "last_dose_unit": None,
                    "status": "disabled",
                }
                continue
            
            if medication_id not in doses or not doses[medication_id]:
                # No doses for this medication yet
                next_doses[medication_id] = {
                    "available_now": True,
                    "next_time": now.isoformat(),  # Available immediately
                    "last_dose_time": None,
                    "last_dose_amount": None,
                    "last_dose_unit": None,
                    "status": "never_taken",
                }
                continue
            
            # Sort doses by timestamp in descending order
            sorted_doses = sorted(
                doses[medication_id], 
                key=lambda x: x["timestamp"], 
                reverse=True
            )
            
            if not sorted_doses:
                next_doses[medication_id] = {
                    "available_now": True,
                    "next_time": now.isoformat(),  # Available immediately
                    "last_dose_time": None,
                    "last_dose_amount": None,
                    "last_dose_unit": None,
                    "status": "never_taken",
                }
                continue
            
            latest_dose = sorted_doses[0]
            frequency_hours = float(medication.get("frequency", 6))  # Default to 6 hours
            
            last_dose_time = datetime.fromisoformat(latest_dose["timestamp"])
            next_dose_time = last_dose_time + timedelta(hours=frequency_hours)
            
            available_now = now >= next_dose_time
            
            status = "available" if available_now else "waiting"
            
            next_doses[medication_id] = {
                "available_now": available_now,
                "next_time": now.isoformat() if available_now else next_dose_time.isoformat(),
                "last_dose_time": last_dose_time.isoformat(),
                "last_dose_amount": latest_dose.get("amount"),
                "last_dose_unit": latest_dose.get("unit"),
                "status": status,
                "time_since_last_dose": (now - last_dose_time).total_seconds() / 3600,  # hours
                "time_until_next_dose": 0 if available_now else (next_dose_time - now).total_seconds() / 3600,  # hours
            }
            
        return next_doses
        
    async def update_medication_entities(self, medication_id: str) -> None:
        """Force update of entities associated with a medication."""
        if DOMAIN not in self.hass.data or 'entities' not in self.hass.data[DOMAIN]:
            return
            
        if medication_id in self.hass.data[DOMAIN]['entities']:
            for entity_id in self.hass.data[DOMAIN]['entities'][medication_id]:
                try:
                    _LOGGER.debug("Requesting update for entity: %s", entity_id)
                    await self.hass.helpers.entity_component.async_update_entity(entity_id)
                except Exception as err:
                    _LOGGER.error("Error updating entity %s: %s", entity_id, err)
        
    async def add_patient(self, patient_data: Dict[str, Any]) -> str:
        """Add a new patient."""
        patient_id = self.storage.add_patient(patient_data)
        await self.storage.async_save()
        await self.async_refresh()
        return patient_id
        
    async def update_patient(self, patient_id: str, patient_data: Dict[str, Any]) -> bool:
        """Update an existing patient."""
        result = self.storage.update_patient(patient_id, patient_data)
        if result:
            await self.storage.async_save()
            await self.async_refresh()
        return result
        
    async def delete_patient(self, patient_id: str) -> bool:
        """Delete a patient."""
        result = self.storage.delete_patient(patient_id)
        if result:
            await self.storage.async_save()
            await self.async_refresh()
        return result
        
    async def add_medication(self, medication_data: Dict[str, Any]) -> str:
        """Add a new medication."""
        medication_id = self.storage.add_medication(medication_data)
        await self.storage.async_save()
        await self.async_refresh()
        return medication_id
        
    async def update_medication(self, medication_id: str, medication_data: Dict[str, Any]) -> bool:
        """Update an existing medication."""
        result = self.storage.update_medication(medication_id, medication_data)
        if result:
            await self.storage.async_save()
            await self.async_refresh()
            # Update entities
            await self.update_medication_entities(medication_id)
        return result
        
    async def toggle_medication_status(self, medication_id: str, enabled: bool) -> bool:
        """Enable or disable a medication."""
        medications = self.storage.get_medications()
        if medication_id not in medications:
            return False
            
        medication = medications[medication_id]
        medication["disabled"] = not enabled
        
        result = self.storage.update_medication(medication_id, medication)
        if result:
            await self.storage.async_save()
            await self.async_refresh()
            # Update entities
            await self.update_medication_entities(medication_id)
        return result
        
    async def delete_medication(self, medication_id: str) -> bool:
        """Delete a medication."""
        result = self.storage.delete_medication(medication_id)
        if result:
            await self.storage.async_save()
            await self.async_refresh()
        return result
        
    async def record_dose(self, medication_id: str, dose_data: Dict[str, Any] = None) -> bool:
        """Record a dose for a medication."""
        if dose_data is None:
            dose_data = {}
            
        if "timestamp" not in dose_data:
            dose_data["timestamp"] = datetime.now().isoformat()
            
        result = self.storage.add_dose(medication_id, dose_data)
        if result:
            # Save updated data
            await self.storage.async_save()
            
            # Force an immediate data refresh
            new_data = await self._async_update_data()
            
            # Update the coordinator with new data
            self.async_set_updated_data(new_data)
            
            # Update entities directly
            await self.update_medication_entities(medication_id)
            
            _LOGGER.debug(
                "Recorded dose for medication %s, updated data and notified listeners",
                medication_id
            )
        return result
        
    async def add_temperature(self, patient_id: str, temperature_data: Dict[str, Any]) -> bool:
        """Record a temperature for a patient."""
        if "timestamp" not in temperature_data:
            temperature_data["timestamp"] = datetime.now().isoformat()
            
        result = self.storage.add_temperature(patient_id, temperature_data)
        if result:
            await self.storage.async_save()
            await self.async_refresh()
        return result
        
    async def async_shutdown(self) -> None:
        """Save data when shutting down."""
        await self.storage.async_save() 