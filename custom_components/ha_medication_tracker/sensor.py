"""Platform for Medication Tracker sensor integration."""
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

    _LOGGER.debug("Setting up Medication Tracker sensors")
    entities = []
    
    # Create entities for each patient
    patients = coordinator.data.get("patients", [])
    _LOGGER.debug("Found %d patients to create sensors for", len(patients))
    
    for patient in patients:
        _LOGGER.debug("Creating sensors for patient: %s", patient.get(ATTR_PATIENT_NAME))
        # Create the patient device info
        device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{patient['id']}")},
            name=patient.get(ATTR_PATIENT_NAME, "Unknown Patient"),
            manufacturer="Medication Tracker",
            model="Patient Profile",
            sw_version="1.0",
        )
        
        # Add patient status sensor
        entities.append(
            PatientStatusSensor(
                coordinator=coordinator,
                entry=entry,
                patient=patient,
                device_info=device_info,
            )
        )
        
        # Add temperature sensor
        entities.append(
            PatientTemperatureSensor(
                coordinator=coordinator,
                entry=entry,
                patient=patient,
                device_info=device_info,
            )
        )
        
        # Add medication sensors for each medication
        patient_medications = [
            med for med_id, med in coordinator.data.get("medications", {}).items()
            if med.get("patient_id") == patient["id"]
        ]
        _LOGGER.debug("Found %d medications for patient %s", len(patient_medications), patient.get(ATTR_PATIENT_NAME))
        
        for medication in patient_medications:
            _LOGGER.debug("Creating sensors for medication: %s", medication.get(ATTR_MEDICATION_NAME))
            # Next dose sensor
            entities.append(
                MedicationNextDoseSensor(
                    coordinator=coordinator,
                    entry=entry,
                    patient=patient,
                    medication=medication,
                    device_info=device_info,
                )
            )
            
            # Last dose sensor
            entities.append(
                MedicationLastDoseSensor(
                    coordinator=coordinator,
                    entry=entry,
                    patient=patient,
                    medication=medication,
                    device_info=device_info,
                )
            )
            
            # Compliance sensor
            entities.append(
                MedicationComplianceSensor(
                    coordinator=coordinator,
                    entry=entry,
                    patient=patient,
                    medication=medication,
                    device_info=device_info,
                )
            )

    _LOGGER.debug("Created %d total sensors", len(entities))
    async_add_entities(entities)

class PatientStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a patient's overall status."""

    def __init__(
        self,
        coordinator: MedicationTrackerCoordinator,
        entry: ConfigEntry,
        patient: Dict[str, Any],
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._patient = patient
        self._entry = entry
        self._attr_device_info = device_info
        self._attr_unique_id = f"{entry.entry_id}_patient_{patient['id']}_status"
        self._attr_name = f"{patient.get(ATTR_PATIENT_NAME, 'Unknown')} Status"
        
        self.entity_description = SensorEntityDescription(
            key="patient_status",
            name=self._attr_name,
            icon="mdi:account-check",
        )

    @property
    def native_value(self) -> str:
        """Return the patient's current status."""
        return "Active"  # Can be expanded with more status types

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        return {
            "weight": self._patient.get(ATTR_PATIENT_WEIGHT),
            "weight_unit": self._patient.get(ATTR_PATIENT_WEIGHT_UNIT, "kg"),
            "age": self._patient.get(ATTR_PATIENT_AGE),
        }

class PatientTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a patient's temperature history."""

    def __init__(
        self,
        coordinator: MedicationTrackerCoordinator,
        entry: ConfigEntry,
        patient: Dict[str, Any],
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._patient = patient
        self._entry = entry
        self._attr_device_info = device_info
        self._attr_unique_id = f"{entry.entry_id}_patient_{patient['id']}_temperature"
        self._attr_name = f"{patient.get(ATTR_PATIENT_NAME, 'Unknown')} Temperature"
        
        self.entity_description = SensorEntityDescription(
            key="temperature",
            name=self._attr_name,
            icon="mdi:thermometer",
            device_class=SensorDeviceClass.TEMPERATURE,
        )

    @property
    def native_value(self) -> Optional[float]:
        """Return the latest temperature."""
        temperatures = self.coordinator.data.get("temperatures", {}).get(self._patient["id"], [])
        if temperatures:
            latest = sorted(temperatures, key=lambda x: x["timestamp"])[-1]
            return latest.get("value")
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return temperature history."""
        temperatures = self.coordinator.data.get("temperatures", {}).get(self._patient["id"], [])
        return {
            "history": sorted(temperatures, key=lambda x: x["timestamp"], reverse=True)[:10],
            "unit": "°C",
        }

class MedicationNextDoseSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing when the next dose is due."""

    def __init__(
        self,
        coordinator: MedicationTrackerCoordinator,
        entry: ConfigEntry,
        patient: Dict[str, Any],
        medication: Dict[str, Any],
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._patient = patient
        self._medication = medication
        self._entry = entry
        self._attr_device_info = device_info
        self._attr_unique_id = f"{entry.entry_id}_medication_{medication['id']}_next_dose"
        self._attr_name = f"Next Dose of {medication.get(ATTR_MEDICATION_NAME, 'Unknown')}"
        
        self.entity_description = SensorEntityDescription(
            key="next_dose",
            name=self._attr_name,
            icon="mdi:clock-time-four",
            device_class=SensorDeviceClass.TIMESTAMP,
        )

    @property
    def native_value(self) -> Optional[datetime]:
        """Return when the next dose is due."""
        next_doses = self.coordinator.data.get("next_doses", {})
        dose_info = next_doses.get(self._medication["id"], {})
        
        if dose_info.get("next_time"):
            return datetime.fromisoformat(dose_info["next_time"])
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional medication information."""
        next_doses = self.coordinator.data.get("next_doses", {})
        dose_info = next_doses.get(self._medication["id"], {})
        
        return {
            "available_now": dose_info.get("available_now", False),
            "last_dose_time": dose_info.get("last_dose_time"),
            "last_dose_amount": dose_info.get("last_dose_amount"),
            "last_dose_unit": dose_info.get("last_dose_unit"),
            "dosage": self._medication.get(ATTR_MEDICATION_DOSAGE),
            "unit": self._medication.get(ATTR_MEDICATION_UNIT),
            "frequency": self._medication.get(ATTR_MEDICATION_FREQUENCY),
            "instructions": self._medication.get(ATTR_MEDICATION_INSTRUCTIONS),
        }

class MedicationLastDoseSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing the last recorded dose."""

    def __init__(
        self,
        coordinator: MedicationTrackerCoordinator,
        entry: ConfigEntry,
        patient: Dict[str, Any],
        medication: Dict[str, Any],
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._patient = patient
        self._medication = medication
        self._entry = entry
        self._attr_device_info = device_info
        self._attr_unique_id = f"{entry.entry_id}_medication_{medication['id']}_last_dose"
        self._attr_name = f"Last Dose of {medication.get(ATTR_MEDICATION_NAME, 'Unknown')}"
        
        self.entity_description = SensorEntityDescription(
            key="last_dose",
            name=self._attr_name,
            icon="mdi:medication",
            device_class=SensorDeviceClass.TIMESTAMP,
        )

    @property
    def native_value(self) -> Optional[datetime]:
        """Return when the last dose was taken."""
        doses = self.coordinator.data.get("doses", {}).get(self._medication["id"], [])
        if doses:
            latest = sorted(doses, key=lambda x: x["timestamp"])[-1]
            return datetime.fromisoformat(latest["timestamp"])
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return dose history."""
        doses = self.coordinator.data.get("doses", {}).get(self._medication["id"], [])
        return {
            "history": sorted(doses, key=lambda x: x["timestamp"], reverse=True)[:10],
        }

class MedicationComplianceSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing medication compliance."""

    def __init__(
        self,
        coordinator: MedicationTrackerCoordinator,
        entry: ConfigEntry,
        patient: Dict[str, Any],
        medication: Dict[str, Any],
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._patient = patient
        self._medication = medication
        self._entry = entry
        self._attr_device_info = device_info
        self._attr_unique_id = f"{entry.entry_id}_medication_{medication['id']}_compliance"
        self._attr_name = f"{medication.get(ATTR_MEDICATION_NAME, 'Unknown')} Compliance"
        
        self.entity_description = SensorEntityDescription(
            key="compliance",
            name=self._attr_name,
            icon="mdi:chart-line",
            native_unit_of_measurement="%",
        )

    @property
    def native_value(self) -> Optional[float]:
        """Return the compliance percentage."""
        # This could be expanded with more sophisticated compliance calculation
        doses = self.coordinator.data.get("doses", {}).get(self._medication["id"], [])
        if not doses:
            return 0
        
        # Simple compliance calculation - can be made more sophisticated
        total_doses = len(doses)
        on_time_doses = sum(1 for dose in doses if not dose.get("late", False))
        return round((on_time_doses / total_doses) * 100, 1) if total_doses > 0 else 0 