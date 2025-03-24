"""Platform for Medication Tracker sensor integration."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, Dict, Optional, List

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
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # Add patient sensors
    patients = coordinator.data.get("patients", {})
    for patient_id, patient in patients.items():
        # Create a device for this patient
        device_info = DeviceInfo(
            identifiers={(DOMAIN, f"patient_{patient_id}")},
            name=f"Patient: {patient.get(ATTR_PATIENT_NAME, 'Unknown')}",
            manufacturer="Medication Tracker",
            model="Patient",
            configuration_url="",
        )
        
        # Add patient info sensor
        entities.append(
            PatientInfoSensor(
                coordinator=coordinator,
                entry=entry,
                patient=patient,
                device_info=device_info,
            )
        )
        
        # Add patient temperature sensor
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
            # Create medication info sensor
            entities.append(
                MedicationInfoSensor(
                    coordinator=coordinator,
                    entry=entry,
                    patient=patient,
                    medication=medication,
                    device_info=device_info,
                )
            )
            
            # Next dose sensor
            entities.append(
                MedicationDoseSensor(
                    coordinator=coordinator,
                    entry=entry,
                    patient=patient,
                    medication=medication,
                    device_info=device_info,
                    sensor_type="next_dose"
                )
            )
            
            # Last dose sensor
            entities.append(
                MedicationDoseSensor(
                    coordinator=coordinator,
                    entry=entry,
                    patient=patient,
                    medication=medication,
                    device_info=device_info,
                    sensor_type="last_dose"
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
    
    # Register entities
    async_add_entities(entities)
    
    # Store entity IDs for targeted updates
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    if 'entities' not in hass.data[DOMAIN]:
        hass.data[DOMAIN]['entities'] = {}
    
    # Store entity IDs by medication ID for targeted updates
    for entity in entities:
        if hasattr(entity, '_medication'):
            medication_id = entity._medication["id"]
            if medication_id not in hass.data[DOMAIN]['entities']:
                hass.data[DOMAIN]['entities'][medication_id] = []
            hass.data[DOMAIN]['entities'][medication_id].append(entity.entity_id)


class PatientInfoSensor(CoordinatorEntity, SensorEntity):
    """Sensor for a patient's basic info."""

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
        self._attr_unique_id = f"{entry.entry_id}_patient_{patient['id']}_info"
        self._attr_name = f"Patient {patient.get(ATTR_PATIENT_NAME, 'Unknown')}"
        
        self.entity_description = SensorEntityDescription(
            key="patient_info",
            name=self._attr_name,
            icon="mdi:account",
            entity_category=EntityCategory.DIAGNOSTIC,
        )

    @property
    def native_value(self) -> str:
        """Return the patient's name."""
        return self._patient.get(ATTR_PATIENT_NAME, "Unknown")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return patient details as attributes."""
        return {
            "age": self._patient.get(ATTR_PATIENT_AGE),
            "weight": self._patient.get(ATTR_PATIENT_WEIGHT),
            "weight_unit": self._patient.get(ATTR_PATIENT_WEIGHT_UNIT),
        }
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Force a state update when coordinator updates
        self.async_write_ha_state()


class PatientTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Sensor for a patient's temperature."""

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
            native_unit_of_measurement="°C",
        )

    @property
    def native_value(self) -> Optional[float]:
        """Return the last recorded temperature."""
        temperatures = self.coordinator.data.get("temperatures", {}).get(self._patient["id"], [])
        if temperatures:
            latest = sorted(temperatures, key=lambda x: x["timestamp"], reverse=True)[0]
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
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Force a state update when coordinator updates
        self.async_write_ha_state()


class MedicationInfoSensor(CoordinatorEntity, SensorEntity):
    """Sensor for medication information."""

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
        self._attr_unique_id = f"{entry.entry_id}_medication_{medication['id']}_info"
        self._attr_name = f"Medication: {medication.get(ATTR_MEDICATION_NAME, 'Unknown')}"
        
        self.entity_description = SensorEntityDescription(
            key="medication_info",
            name=self._attr_name,
            icon="mdi:pill",
            entity_category=EntityCategory.DIAGNOSTIC,
        )

    @property
    def native_value(self) -> str:
        """Return the medication name."""
        return self._medication.get(ATTR_MEDICATION_NAME, "Unknown")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return medication details."""
        return {
            "dosage": self._medication.get(ATTR_MEDICATION_DOSAGE),
            "unit": self._medication.get(ATTR_MEDICATION_UNIT),
            "frequency": self._medication.get(ATTR_MEDICATION_FREQUENCY),
            "instructions": self._medication.get(ATTR_MEDICATION_INSTRUCTIONS),
            "temporary": self._medication.get("temporary", False),
            "disabled": self._medication.get("disabled", False),
        }
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Update medication reference with latest data
        medications = self.coordinator.data.get("medications", {})
        if self._medication["id"] in medications:
            self._medication = medications[self._medication["id"]]
        self.async_write_ha_state()


class MedicationDoseSensor(CoordinatorEntity, SensorEntity):
    """Sensor for medication dose status."""

    def __init__(
        self,
        coordinator: MedicationTrackerCoordinator,
        entry: ConfigEntry,
        patient: Dict[str, Any],
        medication: Dict[str, Any],
        device_info: DeviceInfo,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._patient = patient
        self._medication = medication
        self._entry = entry
        self._sensor_type = sensor_type  # "last_dose" or "next_dose"
        self._attr_device_info = device_info
        self._attr_unique_id = f"{entry.entry_id}_medication_{medication['id']}_{sensor_type}"
        
        med_name = medication.get(ATTR_MEDICATION_NAME, "Unknown")
        sensor_name = "Next Dose" if sensor_type == "next_dose" else "Last Dose"
        self._attr_name = f"{sensor_name} of {med_name}"
        
        self.entity_description = SensorEntityDescription(
            key=sensor_type,
            name=self._attr_name,
            icon="mdi:clock-time-four" if sensor_type == "next_dose" else "mdi:medication",
        )

    @property
    def native_value(self) -> str:
        """Return the sensor state as a formatted string to ensure changes are detected."""
        # Skip if medication is disabled
        if self._medication.get("disabled", False):
            return "Medication disabled" + self._get_unique_suffix()
            
        if self._sensor_type == "last_dose":
            doses = self.coordinator.data.get("doses", {}).get(self._medication["id"], [])
            if doses:
                latest = sorted(doses, key=lambda x: x["timestamp"], reverse=True)[0]
                timestamp = datetime.fromisoformat(latest["timestamp"])
                formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                return f"Last dose at {formatted_time}" + self._get_unique_suffix()
            return "No doses recorded" + self._get_unique_suffix()
        else:  # next_dose
            next_doses = self.coordinator.data.get("next_doses", {})
            dose_info = next_doses.get(self._medication["id"], {})
            
            if dose_info.get("available_now", False):
                return f"Available now ({datetime.now().strftime('%H:%M:%S')})" + self._get_unique_suffix()
            elif dose_info.get("next_time"):
                next_time = datetime.fromisoformat(dose_info["next_time"])
                return f"Next dose at {next_time.strftime('%Y-%m-%d %H:%M:%S')}" + self._get_unique_suffix()
            return "Unknown" + self._get_unique_suffix()
    
    def _get_unique_suffix(self) -> str:
        """Return a unique suffix to ensure state changes are detected."""
        # This ensures the state is always unique even if the text is the same
        now = datetime.now()
        return f" ({now.strftime('%S.%f')})"
            
    @property
    def device_class(self) -> Optional[str]:
        """Return the device class."""
        return None  # We're using string states now, not timestamps
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional information."""
        next_doses = self.coordinator.data.get("next_doses", {})
        dose_info = next_doses.get(self._medication["id"], {})
        doses = self.coordinator.data.get("doses", {}).get(self._medication["id"], [])
        
        attributes = {
            "medication_id": self._medication["id"],
            "medication_name": self._medication.get(ATTR_MEDICATION_NAME),
            "temporary": self._medication.get("temporary", False),
            "disabled": self._medication.get("disabled", False),
        }
        
        if self._sensor_type == "next_dose":
            attributes.update({
                "available_now": dose_info.get("available_now", False),
                "next_time": dose_info.get("next_time"),
                "frequency_hours": self._medication.get("frequency"),
            })
        else:  # last_dose
            if doses:
                latest = sorted(doses, key=lambda x: x["timestamp"], reverse=True)[0]
                attributes.update({
                    "last_dose_time": latest.get("timestamp"),
                    "last_dose_amount": latest.get("amount"),
                    "last_dose_unit": latest.get("unit"),
                    "dose_history": sorted(doses, key=lambda x: x["timestamp"], reverse=True)[:10],
                })
        
        return attributes
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Update medication reference with latest data
        medications = self.coordinator.data.get("medications", {})
        if self._medication["id"] in medications:
            self._medication = medications[self._medication["id"]]
        self.async_write_ha_state()


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
        # Skip if medication is disabled
        if self._medication.get("disabled", False):
            return None
            
        # This could be expanded with more sophisticated compliance calculation
        doses = self.coordinator.data.get("doses", {}).get(self._medication["id"], [])
        if not doses:
            return 0
        
        # Simple compliance calculation - just for demonstration
        return 100.0
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Update medication reference with latest data
        medications = self.coordinator.data.get("medications", {})
        if self._medication["id"] in medications:
            self._medication = medications[self._medication["id"]]
        self.async_write_ha_state() 