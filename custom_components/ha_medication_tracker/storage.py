"""Storage handling for Medication Tracker."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast

from homeassistant.const import EVENT_HOMEASSISTANT_START
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = "ha_medication_tracker"
DATA_SCHEMA = {
    "patients": [],
    "medications": {},
    "doses": {},
    "temperatures": {}
}


class MedicationStorage:
    """Class that handles storage of medication data."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the storage."""
        self.hass = hass
        self.store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: Dict[str, Any] = None

    async def async_load(self) -> Dict[str, Any]:
        """Load the data from disk."""
        if self._data is not None:
            return self._data

        data = await self.store.async_load()
        
        if data is None:
            self._data = dict(DATA_SCHEMA)
        else:
            self._data = data

        return self._data

    async def async_save(self) -> None:
        """Save the data to disk."""
        if self._data is not None:
            await self.store.async_save(self._data)

    def get_patients(self) -> List[Dict[str, Any]]:
        """Get all patients."""
        if not self._data:
            return []
        return self._data["patients"]

    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific patient."""
        for patient in self._data["patients"]:
            if patient.get("id") == patient_id:
                return patient
        return None

    def add_patient(self, patient: Dict[str, Any]) -> str:
        """Add a patient."""
        patient_id = patient.get("id")
        if not patient_id:
            # Generate a unique ID
            patient_id = f"patient_{len(self._data['patients']) + 1}"
            patient["id"] = patient_id
            
        # Check if patient already exists
        existing_patient = self.get_patient(patient_id)
        if existing_patient:
            # Update existing patient
            for key, value in patient.items():
                existing_patient[key] = value
        else:
            # Add new patient
            self._data["patients"].append(patient)
            
        return patient_id

    def remove_patient(self, patient_id: str) -> bool:
        """Remove a patient."""
        for i, patient in enumerate(self._data["patients"]):
            if patient.get("id") == patient_id:
                self._data["patients"].pop(i)
                
                # Clean up related medications
                meds_to_remove = []
                for med_id, med in self._data["medications"].items():
                    if med.get("patient_id") == patient_id:
                        meds_to_remove.append(med_id)
                        
                for med_id in meds_to_remove:
                    self.remove_medication(med_id)
                    
                return True
        return False

    def get_medications(self, patient_id: Optional[str] = None) -> Dict[str, Any]:
        """Get medications, optionally filtered by patient."""
        if not self._data:
            return {}
            
        if patient_id:
            return {
                med_id: med 
                for med_id, med in self._data["medications"].items() 
                if med.get("patient_id") == patient_id
            }
        return self._data["medications"]

    def get_medication(self, medication_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific medication."""
        return self._data["medications"].get(medication_id)

    def add_medication(self, medication: Dict[str, Any]) -> str:
        """Add a medication."""
        medication_id = medication.get("id")
        if not medication_id:
            # Generate a unique ID
            medication_id = f"medication_{len(self._data['medications']) + 1}"
            medication["id"] = medication_id
        
        self._data["medications"][medication_id] = medication
        return medication_id

    def remove_medication(self, medication_id: str) -> bool:
        """Remove a medication."""
        if medication_id in self._data["medications"]:
            del self._data["medications"][medication_id]
            
            # Clean up related doses
            if medication_id in self._data["doses"]:
                del self._data["doses"][medication_id]
                
            return True
        return False

    def get_doses(self, medication_id: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get doses, optionally filtered by medication."""
        if not self._data:
            return {}
            
        if medication_id:
            return {
                med_id: doses
                for med_id, doses in self._data["doses"].items()
                if med_id == medication_id
            }
        return self._data["doses"]

    def add_dose(self, medication_id: str, dose: Dict[str, Any]) -> bool:
        """Add a dose record."""
        if medication_id not in self._data["medications"]:
            return False
            
        if medication_id not in self._data["doses"]:
            self._data["doses"][medication_id] = []
            
        self._data["doses"][medication_id].append(dose)
        return True

    def get_temperatures(self, patient_id: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get temperatures, optionally filtered by patient."""
        if not self._data:
            return {}
            
        if patient_id:
            return {
                pat_id: temps
                for pat_id, temps in self._data["temperatures"].items()
                if pat_id == patient_id
            }
        return self._data["temperatures"]

    def add_temperature(self, patient_id: str, temperature: Dict[str, Any]) -> bool:
        """Add a temperature record."""
        if not self.get_patient(patient_id):
            return False
            
        if patient_id not in self._data["temperatures"]:
            self._data["temperatures"][patient_id] = []
            
        self._data["temperatures"][patient_id].append(temperature)
        return True 