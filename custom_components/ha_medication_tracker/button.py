"""Platform for Medication Tracker button integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import (
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import (
    DOMAIN,
    ATTR_PATIENT_NAME,
    ATTR_MEDICATION_NAME,
    ATTR_MEDICATION_DOSAGE,
    ATTR_MEDICATION_UNIT,
)
from .coordinator import MedicationTrackerCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Medication Tracker buttons."""
    coordinator = hass.data[DOMAIN].get("coordinator")
    if not coordinator:
        _LOGGER.error("Cannot set up buttons - coordinator not found")
        return

    _LOGGER.debug("Setting up Medication Tracker buttons")
    entities = []

    # Create buttons for each patient
    patients = coordinator.data.get("patients", [])
    _LOGGER.debug("Found %d patients to create buttons for", len(patients))

    for patient in patients:
        _LOGGER.debug(
            "Creating buttons for patient: %s", patient.get(ATTR_PATIENT_NAME)
        )
        # Create the patient device info
        device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{patient['id']}")},
            name=patient.get(ATTR_PATIENT_NAME, "Unknown Patient"),
            manufacturer="Medication Tracker",
            model="Patient Profile",
            sw_version="1.0",
        )

        # Add temperature recording button
        entities.append(
            RecordTemperatureButton(
                coordinator=coordinator,
                entry=entry,
                patient=patient,
                device_info=device_info,
            )
        )

        # Add medication dose buttons for each medication
        patient_medications = [
            med
            for med_id, med in coordinator.data.get("medications", {}).items()
            if med.get("patient_id") == patient["id"]
        ]
        _LOGGER.debug(
            "Found %d medications for patient %s",
            len(patient_medications),
            patient.get(ATTR_PATIENT_NAME),
        )

        for medication in patient_medications:
            _LOGGER.debug(
                "Creating button for medication: %s",
                medication.get(ATTR_MEDICATION_NAME),
            )
            entities.append(
                RecordDoseButton(
                    coordinator=coordinator,
                    entry=entry,
                    patient=patient,
                    medication=medication,
                    device_info=device_info,
                )
            )

    _LOGGER.debug("Created %d total buttons", len(entities))
    async_add_entities(entities)


class RecordDoseButton(CoordinatorEntity, ButtonEntity):
    """Button for recording a medication dose."""

    def __init__(
        self,
        coordinator: MedicationTrackerCoordinator,
        entry: ConfigEntry,
        patient: dict[str, Any],
        medication: dict[str, Any],
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._patient = patient
        self._medication = medication
        self._entry = entry
        self._attr_device_info = device_info
        self._attr_unique_id = (
            f"{entry.entry_id}_medication_{medication['id']}_record_dose"
        )
        self._attr_name = (
            f"Record Dose of {medication.get(ATTR_MEDICATION_NAME, 'Unknown')}"
        )

        self.entity_description = ButtonEntityDescription(
            key="record_dose",
            name=self._attr_name,
            icon="mdi:pill",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            # Create the service data with default values from medication
            service_data = {
                "medication_id": self._medication["id"],
                "dose_amount": self._medication.get(ATTR_MEDICATION_DOSAGE),
                "dose_unit": self._medication.get(ATTR_MEDICATION_UNIT),
            }

            # Call the service
            await self.hass.services.async_call(
                DOMAIN,
                "record_dose",
                service_data,
                blocking=True,
            )
            await self.coordinator.async_request_refresh()
        except (ValueError, KeyError, Exception) as ex:
            _LOGGER.error("Failed to record dose: %s", ex)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "default_dosage": self._medication.get(ATTR_MEDICATION_DOSAGE),
            "default_unit": self._medication.get(ATTR_MEDICATION_UNIT),
            "patient_name": self._patient.get(ATTR_PATIENT_NAME),
            "medication_name": self._medication.get(ATTR_MEDICATION_NAME),
        }


class RecordTemperatureButton(CoordinatorEntity, ButtonEntity):
    """Button for recording a patient's temperature."""

    def __init__(
        self,
        coordinator: MedicationTrackerCoordinator,
        entry: ConfigEntry,
        patient: dict[str, Any],
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._patient = patient
        self._entry = entry
        self._attr_device_info = device_info
        self._attr_unique_id = (
            f"{entry.entry_id}_patient_{patient['id']}_record_temperature"
        )
        self._attr_name = (
            f"Record Temperature for {patient.get(ATTR_PATIENT_NAME, 'Unknown')}"
        )

        self.entity_description = ButtonEntityDescription(
            key="record_temperature",
            name=self._attr_name,
            icon="mdi:thermometer",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            # Create the service data
            service_data = {
                "patient_id": self._patient["id"],
                "temperature_value": 37.0,  # Default temperature
            }

            # Call the service
            await self.hass.services.async_call(
                DOMAIN,
                "record_temperature",
                service_data,
                blocking=True,
            )
            await self.coordinator.async_request_refresh()
        except (ValueError, KeyError, Exception) as ex:
            _LOGGER.error("Failed to record temperature: %s", ex)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "patient_name": self._patient.get(ATTR_PATIENT_NAME),
            "default_unit": "°C",
        }
