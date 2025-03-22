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

from .const import DOMAIN
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

    entities = []

    # Add a next dose sensor
    entities.append(MedicationNextDoseSensor(coordinator, entry))

    # Add patient sensors
    for patient in coordinator.data.get("patients", []):
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
        patient: Dict[str, Any],
    ) -> None:
        """Initialize the patient sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._patient = patient
        self._attr_unique_id = f"{entry.entry_id}_patient_{patient['id']}"
        
        # Set the entity name to the patient's name
        self._attr_name = patient.get("name", "Unknown Patient")
        
        # Create a custom entity description for this patient
        self.entity_description = SensorEntityDescription(
            key=f"patient_{patient['id']}",
            name=self._attr_name,
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
        return self._patient.get("name", "Unknown")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}

        patient_id = self._patient["id"]
        attributes = {
            "id": patient_id,
            "weight": self._patient.get("weight"),
            "weight_unit": self._patient.get("weight_unit", "kg"),
            "age": self._patient.get("age"),
        }

        # Add medication information
        medications = []
        for med_id, med in self.coordinator.data.get("medications", {}).items():
            if med.get("patient_id") == patient_id:
                next_dose_info = self.coordinator.data.get("next_doses", {}).get(med_id, {})
                medication_info = {
                    "name": med.get("name"),
                    "dosage": med.get("dosage"),
                    "unit": med.get("unit"),
                    "frequency": med.get("frequency"),
                    "instructions": med.get("instructions"),
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

        return attributes 