"""Platform for Medication Tracker switch integration."""
from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription,
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
)
from .coordinator import MedicationTrackerCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Medication Tracker switches."""
    coordinator = hass.data[DOMAIN].get("coordinator")
    if not coordinator:
        _LOGGER.error("Cannot set up switches - coordinator not found")
        return

    _LOGGER.debug("Setting up Medication Tracker switches")
    entities = []
    
    # Create switches for each patient's medications
    patients = coordinator.data.get("patients", [])
    _LOGGER.debug("Found %d patients to create switches for", len(patients))
    
    for patient in patients:
        _LOGGER.debug("Creating switches for patient: %s", patient.get(ATTR_PATIENT_NAME))
        # Create the patient device info
        device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{patient['id']}")},
            name=patient.get(ATTR_PATIENT_NAME, "Unknown Patient"),
            manufacturer="Medication Tracker",
            model="Patient Profile",
            sw_version="1.0",
        )
        
        # Add medication tracking switches for each medication
        patient_medications = [
            med for med_id, med in coordinator.data.get("medications", {}).items()
            if med.get("patient_id") == patient["id"]
        ]
        _LOGGER.debug("Found %d medications for patient %s", len(patient_medications), patient.get(ATTR_PATIENT_NAME))
        
        for medication in patient_medications:
            _LOGGER.debug("Creating switch for medication: %s", medication.get(ATTR_MEDICATION_NAME))
            entities.append(
                MedicationTrackingSwitch(
                    coordinator=coordinator,
                    entry=entry,
                    patient=patient,
                    medication=medication,
                    device_info=device_info,
                )
            )

    _LOGGER.debug("Created %d total switches", len(entities))
    async_add_entities(entities)

class MedicationTrackingSwitch(CoordinatorEntity, SwitchEntity):
    """Switch for enabling/disabling medication tracking."""

    def __init__(
        self,
        coordinator: MedicationTrackerCoordinator,
        entry: ConfigEntry,
        patient: Dict[str, Any],
        medication: Dict[str, Any],
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._patient = patient
        self._medication = medication
        self._entry = entry
        self._attr_device_info = device_info
        self._attr_unique_id = f"{entry.entry_id}_medication_{medication['id']}_tracking"
        self._attr_name = f"Track {medication.get(ATTR_MEDICATION_NAME, 'Unknown')}"
        
        self.entity_description = SwitchEntityDescription(
            key="medication_tracking",
            name=self._attr_name,
            icon="mdi:medication",
        )

    @property
    def is_on(self) -> bool:
        """Return True if tracking is enabled."""
        return not self._medication.get("disabled", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable tracking for this medication."""
        self._medication["disabled"] = False
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable tracking for this medication."""
        self._medication["disabled"] = True
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        return {
            "patient_name": self._patient.get(ATTR_PATIENT_NAME),
            "medication_name": self._medication.get(ATTR_MEDICATION_NAME),
        } 