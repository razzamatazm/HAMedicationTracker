"""Sensor platform for the Medication Tracker integration."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN
from .coordinator import MedicationTrackerCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Medication Tracker sensors."""
    # Get the coordinator
    coordinator = hass.data[DOMAIN].get("coordinator")
    if not coordinator:
        _LOGGER.error("Cannot set up sensors - coordinator not found")
        return
    
    # Create a list of entities
    entities = []
    
    # Add a next dose sensor
    entities.append(MedicationNextDoseSensor(coordinator, entry))
    
    # For each patient, add a sensor
    for patient in coordinator.data.get("patients", []):
        entities.append(PatientSensor(coordinator, entry, patient))
    
    # For each medication, add a sensor
    for medication_id, medication in coordinator.data.get("medications", {}).items():
        entities.append(MedicationSensor(coordinator, entry, medication_id, medication))
    
    async_add_entities(entities)


class MedicationNextDoseSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing the next available dose for medications."""

    def __init__(self, coordinator: MedicationTrackerCoordinator, entry: ConfigEntry) -> None:
        """Initialize the next dose sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_next_doses"
        self._attr_name = "Medication Next Doses"
        self._attr_has_entity_name = True
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Medication Tracker",
            manufacturer="Home Assistant Community",
            model="Medication Tracker",
            sw_version="0.1.0",
        )

    @property
    def native_value(self) -> Optional[datetime]:
        """Return the next upcoming dose time."""
        if not self.coordinator.data or "next_doses" not in self.coordinator.data:
            return None
            
        next_doses = self.coordinator.data["next_doses"]
        upcoming_times = []
        
        for medication_id, dose_info in next_doses.items():
            if dose_info.get("next_time") and not dose_info.get("available_now", False):
                upcoming_times.append(datetime.fromisoformat(dose_info["next_time"]))
                
        if not upcoming_times:
            return None
            
        # Return the soonest upcoming dose time
        return min(upcoming_times)
        
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data or "next_doses" not in self.coordinator.data:
            return {}
            
        attributes = {}
        medications = self.coordinator.data.get("medications", {})
        next_doses = self.coordinator.data.get("next_doses", {})
        
        for medication_id, medication in medications.items():
            med_name = medication.get("name", medication_id)
            
            if medication_id in next_doses:
                dose_info = next_doses[medication_id]
                if dose_info.get("available_now", False):
                    attributes[f"{med_name}_available"] = "Available now"
                elif dose_info.get("next_time"):
                    next_time = datetime.fromisoformat(dose_info["next_time"])
                    attributes[f"{med_name}_next_dose"] = next_time.isoformat()
                    
        return attributes


class PatientSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a patient."""

    def __init__(
        self, 
        coordinator: MedicationTrackerCoordinator, 
        entry: ConfigEntry,
        patient: Dict[str, Any]
    ) -> None:
        """Initialize the patient sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._patient = patient
        patient_id = patient.get("id", "unknown")
        
        self._attr_unique_id = f"{entry.entry_id}_patient_{patient_id}"
        self._attr_name = f"Patient {patient.get('name', patient_id)}"
        self._attr_has_entity_name = True
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Medication Tracker",
            manufacturer="Home Assistant Community",
            model="Medication Tracker",
            sw_version="0.1.0",
        )

    @property
    def native_value(self) -> str:
        """Return the patient's name."""
        return self._patient.get("name", "Unknown")
        
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        # Find the latest temperature for this patient
        patient_id = self._patient.get("id")
        temperatures = self.coordinator.data.get("temperatures", {}).get(patient_id, [])
        
        attributes = {
            "id": patient_id,
            "weight": self._patient.get("weight"),
            "weight_unit": self._patient.get("weight_unit", "kg"),
            "age": self._patient.get("age"),
        }
        
        if temperatures:
            # Sort by timestamp in descending order
            sorted_temps = sorted(
                temperatures, 
                key=lambda x: x["timestamp"], 
                reverse=True
            )
            
            if sorted_temps:
                latest_temp = sorted_temps[0]
                attributes["last_temperature"] = latest_temp.get("value")
                attributes["last_temperature_unit"] = latest_temp.get("unit", "°C")
                attributes["last_temperature_time"] = latest_temp.get("timestamp")
                
        return attributes


class MedicationSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a medication."""

    def __init__(
        self, 
        coordinator: MedicationTrackerCoordinator, 
        entry: ConfigEntry,
        medication_id: str,
        medication: Dict[str, Any]
    ) -> None:
        """Initialize the medication sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._medication_id = medication_id
        self._medication = medication
        
        self._attr_unique_id = f"{entry.entry_id}_medication_{medication_id}"
        self._attr_name = f"Medication {medication.get('name', medication_id)}"
        self._attr_has_entity_name = True
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Medication Tracker",
            manufacturer="Home Assistant Community",
            model="Medication Tracker",
            sw_version="0.1.0",
        )

    @property
    def native_value(self) -> str:
        """Return the medication status."""
        next_doses = self.coordinator.data.get("next_doses", {})
        
        if self._medication_id in next_doses:
            dose_info = next_doses[self._medication_id]
            if dose_info.get("available_now", False):
                return "Available now"
            elif dose_info.get("next_time"):
                return "Upcoming"
        
        return "Unknown"
        
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        next_doses = self.coordinator.data.get("next_doses", {})
        doses = self.coordinator.data.get("doses", {}).get(self._medication_id, [])
        
        attributes = {
            "id": self._medication_id,
            "name": self._medication.get("name"),
            "patient_id": self._medication.get("patient_id"),
            "dosage": self._medication.get("dosage"),
            "unit": self._medication.get("unit", "mg"),
            "frequency": self._medication.get("frequency", 6),
            "max_daily_doses": self._medication.get("max_daily_doses"),
            "instructions": self._medication.get("instructions"),
        }
        
        # Add next dose information
        if self._medication_id in next_doses:
            dose_info = next_doses[self._medication_id]
            attributes["available_now"] = dose_info.get("available_now", False)
            if dose_info.get("next_time"):
                attributes["next_dose_time"] = dose_info.get("next_time")
                
        # Add last dose information
        if doses:
            # Sort by timestamp in descending order
            sorted_doses = sorted(
                doses, 
                key=lambda x: x["timestamp"], 
                reverse=True
            )
            
            if sorted_doses:
                latest_dose = sorted_doses[0]
                attributes["last_dose_time"] = latest_dose.get("timestamp")
                attributes["last_dose_amount"] = latest_dose.get("amount")
                attributes["last_dose_unit"] = latest_dose.get("unit")
                
        return attributes 