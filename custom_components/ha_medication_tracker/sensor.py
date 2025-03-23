"""Sensor platform for the Medication Tracker integration."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
    ATTR_PATIENT_NAME,
    ATTR_PATIENT_WEIGHT,
    ATTR_PATIENT_WEIGHT_UNIT,
    ATTR_PATIENT_AGE,
    ATTR_MEDICATION_NAME,
    ATTR_MEDICATION_DOSAGE,
    ATTR_MEDICATION_UNIT,
    ATTR_MEDICATION_FREQUENCY,
    ATTR_MEDICATION_INSTRUCTIONS,
)
from .coordinator import MedicationTrackerCoordinator

_LOGGER = logging.getLogger(__name__)

NEXT_DOSES_DESCRIPTION = SensorEntityDescription(
    key="next_doses",
    name="Medication Next Doses",
    icon="mdi:clock-time-four",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Medication Tracker sensors."""
    coordinator = hass.data[DOMAIN].get("coordinator")
    if not coordinator:
        _LOGGER.error("Cannot set up sensors - coordinator not found")
        return

    _LOGGER.debug("Setting up sensors with coordinator data: %s", coordinator.data)
    
    entities = []

    # Add a next dose sensor
    entities.append(MedicationNextDoseSensor(coordinator, entry))

    # Add patient sensors
    patients = coordinator.data.get("patients", [])
    _LOGGER.debug("Creating sensors for patients: %s", patients)
    
    for patient in patients:
        _LOGGER.debug("Creating sensor for patient: %s", patient)
        entities.append(PatientSensor(coordinator, entry, patient))

    async_add_entities(entities)


class MedicationNextDoseSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing the next available dose for medications."""

    def __init__(self, coordinator: MedicationTrackerCoordinator, entry: ConfigEntry) -> None:
        """Initialize the next dose sensor."""
        super().__init__(coordinator)
        self.entity_description = NEXT_DOSES_DESCRIPTION
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_next_doses"
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
        if not self.coordinator.data:
            return {}

        attributes = {}
        medications = self.coordinator.data.get("medications", {})
        next_doses = self.coordinator.data.get("next_doses", {})

        for medication_id, medication in medications.items():
            med_name = medication.get(ATTR_MEDICATION_NAME, medication_id)

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
        patient: Dict[str, Any],
    ) -> None:
        """Initialize the patient sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._patient = patient
        self._attr_unique_id = f"{entry.entry_id}_patient_{patient['id']}"
        
        # Get patient name from either the new or old field name
        patient_name = patient.get(ATTR_PATIENT_NAME) or patient.get("name", "Unknown Patient")
        self._attr_name = patient_name
        _LOGGER.debug("Creating patient sensor with name: %s", self._attr_name)
        
        # Create a custom entity description for this patient
        self.entity_description = SensorEntityDescription(
            key=f"patient_{patient['id']}",
            name=patient_name,
            icon="mdi:account",
        )

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
        name = self._patient.get(ATTR_PATIENT_NAME) or self._patient.get("name", "Unknown")
        _LOGGER.debug("Patient sensor %s returning native value: %s", self._attr_unique_id, name)
        return name

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}

        patient_id = self._patient["id"]
        attributes = {
            "id": patient_id,
            "weight": self._patient.get(ATTR_PATIENT_WEIGHT) or self._patient.get("weight"),
            "weight_unit": self._patient.get(ATTR_PATIENT_WEIGHT_UNIT) or self._patient.get("weight_unit", "kg"),
            "age": self._patient.get(ATTR_PATIENT_AGE) or self._patient.get("age"),
        }

        # Add medication information
        medications = []
        for med_id, med in self.coordinator.data.get("medications", {}).items():
            if med.get("patient_id") == patient_id:
                next_dose_info = self.coordinator.data.get("next_doses", {}).get(med_id, {})
                medication_info = {
                    "name": med.get(ATTR_MEDICATION_NAME),
                    "dosage": med.get(ATTR_MEDICATION_DOSAGE),
                    "unit": med.get(ATTR_MEDICATION_UNIT),
                    "frequency": med.get(ATTR_MEDICATION_FREQUENCY),
                    "instructions": med.get(ATTR_MEDICATION_INSTRUCTIONS),
                    "available_now": next_dose_info.get("available_now", False),
                    "next_dose": next_dose_info.get("next_time"),
                }
                medications.append(medication_info)

        attributes["medications"] = medications

        # Add temperature information
        temperatures = self.coordinator.data.get("temperatures", {}).get(patient_id, [])
        if temperatures:
            latest_temp = sorted(temperatures, key=lambda x: x["timestamp"])[-1]
            attributes.update({
                "last_temperature": latest_temp.get("value"),
                "last_temperature_unit": latest_temp.get("unit", "°C"),
                "last_temperature_time": latest_temp.get("timestamp"),
            })

        _LOGGER.debug("Patient sensor %s attributes: %s", self._attr_unique_id, attributes)
        return attributes 