"""Storage for Medication Tracker."""
import json
import logging
import os
from typing import Any, Dict, List, Optional
import uuid

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
import voluptuous as vol

from .const import DOMAIN, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

class MedicationStorage:
    """Class to store medication data."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize storage."""
        self.hass = hass
        self.store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.storage")
        self._data = None
        self._loaded = False

    async def async_load(self) -> None:
        """Load data from disk."""
        if self._loaded:
            return

        data = await self.store.async_load()
        if data:
            self._data = data
        else:
            self._data = {
                "patients": {},
                "medications": {},
                "doses": {},
                "temperatures": {},
            }
        self._loaded = True

    async def async_save(self) -> None:
        """Save data to disk."""
        if not self._loaded:
            await self.async_load()
        await self.store.async_save(self._data)

    def _ensure_loaded(self) -> None:
        """Ensure data is loaded."""
        if not self._loaded:
            self.hass.loop.run_until_complete(self.async_load())

    def get_patients(self) -> Dict[str, Any]:
        """Get all patients."""
        self._ensure_loaded()
        return self._data["patients"]

    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get a patient by ID."""
        self._ensure_loaded()
        return self._data["patients"].get(patient_id)

    def add_patient(self, patient_data: Dict[str, Any]) -> str:
        """Add a new patient."""
        self._ensure_loaded()
        
        # Generate a unique ID
        patient_id = str(uuid.uuid4())
        patient_data["id"] = patient_id
        
        # Add to storage
        self._data["patients"][patient_id] = patient_data
        
        return patient_id

    def update_patient(self, patient_id: str, patient_data: Dict[str, Any]) -> bool:
        """Update an existing patient."""
        self._ensure_loaded()
        
        if patient_id not in self._data["patients"]:
            return False
            
        # Update with new data
        self._data["patients"][patient_id].update(patient_data)
        
        return True

    def delete_patient(self, patient_id: str) -> bool:
        """Delete a patient."""
        self._ensure_loaded()
        
        if patient_id not in self._data["patients"]:
            return False
            
        # Remove the patient
        self._data["patients"].pop(patient_id)
        
        # Remove associated medications
        med_ids_to_remove = []
        for med_id, med in self._data["medications"].items():
            if med.get("patient_id") == patient_id:
                med_ids_to_remove.append(med_id)
                
        for med_id in med_ids_to_remove:
            self._data["medications"].pop(med_id)
            if med_id in self._data["doses"]:
                self._data["doses"].pop(med_id)
        
        # Remove temperatures
        if patient_id in self._data["temperatures"]:
            self._data["temperatures"].pop(patient_id)
            
        return True

    def get_medications(self) -> Dict[str, Any]:
        """Get all medications."""
        self._ensure_loaded()
        return self._data["medications"]

    def get_medication(self, medication_id: str) -> Optional[Dict[str, Any]]:
        """Get a medication by ID."""
        self._ensure_loaded()
        return self._data["medications"].get(medication_id)

    def add_medication(self, medication_data: Dict[str, Any]) -> str:
        """Add a new medication."""
        self._ensure_loaded()
        
        # Generate a unique ID
        medication_id = str(uuid.uuid4())
        medication_data["id"] = medication_id
        
        # Set defaults for new medication
        if "temporary" not in medication_data:
            medication_data["temporary"] = False
        if "disabled" not in medication_data:
            medication_data["disabled"] = False
        
        # Add to storage
        self._data["medications"][medication_id] = medication_data
        
        return medication_id

    def update_medication(self, medication_id: str, medication_data: Dict[str, Any]) -> bool:
        """Update an existing medication."""
        self._ensure_loaded()
        
        if medication_id not in self._data["medications"]:
            return False
            
        # Update with new data while preserving the ID
        medication_data["id"] = medication_id
        self._data["medications"][medication_id] = medication_data
        
        return True

    def delete_medication(self, medication_id: str) -> bool:
        """Delete a medication."""
        self._ensure_loaded()
        
        if medication_id not in self._data["medications"]:
            return False
            
        # Remove the medication
        self._data["medications"].pop(medication_id)
        
        # Remove associated doses
        if medication_id in self._data["doses"]:
            self._data["doses"].pop(medication_id)
            
        return True

    def get_doses(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all doses."""
        self._ensure_loaded()
        return self._data["doses"]

    def get_medication_doses(self, medication_id: str) -> List[Dict[str, Any]]:
        """Get doses for a medication."""
        self._ensure_loaded()
        return self._data["doses"].get(medication_id, [])

    def add_dose(self, medication_id: str, dose_data: Dict[str, Any]) -> bool:
        """Add a new dose for a medication."""
        self._ensure_loaded()
        
        if medication_id not in self._data["medications"]:
            _LOGGER.error("Cannot add dose for unknown medication: %s", medication_id)
            return False
            
        # Ensure there's a record for this medication
        if medication_id not in self._data["doses"]:
            self._data["doses"][medication_id] = []
            
        # Add the dose
        self._data["doses"][medication_id].append(dose_data)
        
        return True

    def get_temperatures(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all temperatures."""
        self._ensure_loaded()
        return self._data["temperatures"]

    def get_patient_temperatures(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get temperatures for a patient."""
        self._ensure_loaded()
        return self._data["temperatures"].get(patient_id, [])

    def add_temperature(self, patient_id: str, temperature_data: Dict[str, Any]) -> bool:
        """Add a new temperature for a patient."""
        self._ensure_loaded()
        
        if patient_id not in self._data["patients"]:
            return False
            
        # Ensure there's a record for this patient
        if patient_id not in self._data["temperatures"]:
            self._data["temperatures"][patient_id] = []
            
        # Add the temperature
        self._data["temperatures"][patient_id].append(temperature_data)
        
        return True 