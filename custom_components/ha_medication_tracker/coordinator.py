"""Medication Tracker Coordinator for handling data."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

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
            update_interval=timedelta(minutes=1),
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
                }
                continue
            
            if medication_id not in doses or not doses[medication_id]:
                # No doses for this medication yet
                next_doses[medication_id] = {
                    "available_now": True,
                    "next_time": None,
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
                    "next_time": None,
                }
                continue
            
            latest_dose = sorted_doses[0]
            frequency_hours = float(medication.get("frequency", 6))  # Default to 6 hours, ensure it's a float
            
            try:
                last_dose_time = datetime.fromisoformat(latest_dose["timestamp"])
                next_dose_time = last_dose_time + timedelta(hours=frequency_hours)
                
                available_now = now >= next_dose_time
                
                next_doses[medication_id] = {
                    "available_now": available_now,
                    "next_time": next_dose_time.isoformat() if not available_now else None,
                    "last_dose_time": last_dose_time.isoformat(),
                    "last_dose_amount": latest_dose.get("amount"),
                    "last_dose_unit": latest_dose.get("unit"),
                }
            except (ValueError, TypeError) as err:
                _LOGGER.error("Error calculating next dose for medication %s: %s", medication_id, err)
                next_doses[medication_id] = {
                    "available_now": True,  # Default to available if we can't calculate
                    "next_time": None,
                    "last_dose_time": latest_dose.get("timestamp"),
                    "last_dose_amount": latest_dose.get("amount"),
                    "last_dose_unit": latest_dose.get("unit"),
                }
            
        return next_doses
        
    async def add_patient(self, patient_data: Dict[str, Any]) -> str:
        """Add a new patient."""
        patient_id = self.storage.add_patient(patient_data)
        await self.storage.async_save()
        await self.async_refresh()
        return patient_id
        
    async def remove_patient(self, patient_id: str) -> bool:
        """Remove a patient."""
        result = self.storage.remove_patient(patient_id)
        await self.storage.async_save()
        await self.async_refresh()
        return result
        
    async def add_medication(self, medication_data: Dict[str, Any]) -> str:
        """Add a new medication for a patient."""
        medication_id = self.storage.add_medication(medication_data)
        await self.storage.async_save()
        await self.async_refresh()
        return medication_id
        
    async def remove_medication(self, medication_id: str) -> bool:
        """Remove a medication."""
        result = self.storage.remove_medication(medication_id)
        await self.storage.async_save()
        await self.async_refresh()
        return result
        
    async def record_dose(self, medication_id: str, dose_data: Dict[str, Any] = None) -> bool:
        """Record a dose for a medication."""
        if dose_data is None:
            dose_data = {}
            
        if "timestamp" not in dose_data:
            dose_data["timestamp"] = datetime.now().isoformat()
        
        _LOGGER.debug("Recording dose for medication %s: %s", medication_id, dose_data)
        
        # Get medication info for better logging
        medication = self.storage.get_medication(medication_id)
        if medication:
            _LOGGER.debug("Medication found: %s", medication.get("name", medication_id))
        else:
            _LOGGER.warning("Medication with ID %s not found", medication_id)
            
        result = self.storage.add_dose(medication_id, dose_data)
        
        if result:
            _LOGGER.debug("Dose recorded successfully, saving and refreshing")
            await self.storage.async_save()
            
            # Force immediate refresh
            try:
                fresh_data = await self._async_update_data()
                self.async_set_updated_data(fresh_data)
                _LOGGER.debug("Data updated with new dose information: %s", 
                            fresh_data.get("doses", {}).get(medication_id, [])[-1:])
            except Exception as err:
                _LOGGER.error("Error refreshing data after dose record: %s", err)
            
        return result
        
    async def record_temperature(self, patient_id: str, temperature_data: Dict[str, Any] = None) -> bool:
        """Record a temperature for a patient."""
        if temperature_data is None:
            temperature_data = {}
            
        if "timestamp" not in temperature_data:
            temperature_data["timestamp"] = datetime.now().isoformat()
            
        result = self.storage.add_temperature(patient_id, temperature_data)
        await self.storage.async_save()
        await self.async_refresh()
        return result
        
    async def async_shutdown(self) -> None:
        """Save data when shutting down."""
        await self.storage.async_save() 