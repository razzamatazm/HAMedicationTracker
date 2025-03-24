"""Config flow for Medication Tracker integration."""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    DEFAULT_NAME,
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

_LOGGER = logging.getLogger(__name__)

# Schema for adding a patient
ADD_PATIENT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PATIENT_NAME): str,
        vol.Optional(ATTR_PATIENT_WEIGHT): vol.Coerce(float),
        vol.Optional(ATTR_PATIENT_WEIGHT_UNIT, default="kg"): vol.In(["kg", "lb"]),
        vol.Optional(ATTR_PATIENT_AGE): vol.Coerce(int),
    }
)

# Schema for adding a medication
ADD_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MEDICATION_NAME): str,
        vol.Optional(ATTR_MEDICATION_DOSAGE): vol.Coerce(float),
        vol.Optional(ATTR_MEDICATION_UNIT, default="mg"): str,
        vol.Optional(ATTR_MEDICATION_FREQUENCY, default=6): vol.Coerce(float),
        vol.Optional(ATTR_MEDICATION_INSTRUCTIONS): str,
    }
)

# Schema for patient selection
PATIENT_SELECTION_SCHEMA = vol.Schema(
    {
        vol.Required("action"): vol.In(["add", "done"])
    }
)

# Schema for medication selection
MEDICATION_SELECTION_SCHEMA = vol.Schema(
    {
        vol.Required("action"): vol.In(["add", "done"])
    }
)

class HaMedicationTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Medication Tracker."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.patients = []
        self.medications = {}
        self.current_patient = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        return await self.async_step_patient_selection()

    async def async_step_patient_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle patient selection."""
        if user_input is not None:
            if user_input["action"] == "done":
                if not self.patients:
                    return self.async_show_form(
                        step_id="patient_selection",
                        data_schema=PATIENT_SELECTION_SCHEMA,
                        errors={"base": "no_patients"},
                        description_placeholders={
                            "patient_count": "0",
                            "patient_list": "",
                        },
                    )
                return self.async_create_entry(
                    title="Medication Tracker",
                    data={
                        "name": "Medication Tracker",
                        "patients": self.patients,
                        "medications": self.medications,
                        "doses": {},
                        "temperatures": {},
                    },
                )
            return await self.async_step_add_patient()

        return self.async_show_form(
            step_id="patient_selection",
            data_schema=PATIENT_SELECTION_SCHEMA,
            description_placeholders={
                "patient_count": str(len(self.patients)),
                "patient_list": ", ".join(p.get(ATTR_PATIENT_NAME, "") for p in self.patients),
            },
        )

    async def async_step_add_patient(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding a patient."""
        errors = {}

        if user_input is not None:
            try:
                patient_id = str(uuid.uuid4())
                patient_data = {
                    "id": patient_id,
                    ATTR_PATIENT_NAME: user_input[ATTR_PATIENT_NAME],
                    ATTR_PATIENT_WEIGHT: user_input.get(ATTR_PATIENT_WEIGHT),
                    ATTR_PATIENT_WEIGHT_UNIT: user_input.get(ATTR_PATIENT_WEIGHT_UNIT, "kg"),
                    ATTR_PATIENT_AGE: user_input.get(ATTR_PATIENT_AGE),
                }
                self.patients.append(patient_data)
                self.current_patient = patient_data
                return await self.async_step_medication_selection()
            except Exception as ex:
                _LOGGER.exception("Error adding patient: %s", ex)
                errors["base"] = "add_failed"

        return self.async_show_form(
            step_id="add_patient",
            data_schema=ADD_PATIENT_SCHEMA,
            errors=errors,
        )

    async def async_step_medication_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle medication selection for the current patient."""
        if user_input is not None:
            if user_input["action"] == "done":
                return await self.async_step_patient_selection()
            return await self.async_step_add_medication()

        # Get medications for current patient
        patient_medications = [
            med for med_id, med in self.medications.items()
            if med.get("patient_id") == self.current_patient["id"]
        ]

        return self.async_show_form(
            step_id="medication_selection",
            data_schema=MEDICATION_SELECTION_SCHEMA,
            description_placeholders={
                "patient_name": self.current_patient.get(ATTR_PATIENT_NAME, "Unknown"),
                "medication_count": str(len(patient_medications)),
                "medication_list": ", ".join(med.get(ATTR_MEDICATION_NAME, "") for med in patient_medications),
            },
        )

    async def async_step_add_medication(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding a medication."""
        errors = {}

        if user_input is not None:
            try:
                medication_id = str(uuid.uuid4())
                medication_data = {
                    "id": medication_id,
                    "patient_id": self.current_patient["id"],
                    ATTR_MEDICATION_NAME: user_input[ATTR_MEDICATION_NAME],
                    ATTR_MEDICATION_DOSAGE: user_input.get(ATTR_MEDICATION_DOSAGE),
                    ATTR_MEDICATION_UNIT: user_input.get(ATTR_MEDICATION_UNIT, "mg"),
                    ATTR_MEDICATION_FREQUENCY: user_input.get(ATTR_MEDICATION_FREQUENCY, 6),
                    ATTR_MEDICATION_INSTRUCTIONS: user_input.get(ATTR_MEDICATION_INSTRUCTIONS),
                }
                self.medications[medication_id] = medication_data
                return await self.async_step_medication_selection()
            except Exception as ex:
                _LOGGER.exception("Error adding medication: %s", ex)
                errors["base"] = "add_failed"

        return self.async_show_form(
            step_id="add_medication",
            data_schema=ADD_MEDICATION_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for the integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.selected_patient_id = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return await self.async_step_menu()

    async def async_step_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the configuration menu."""
        if user_input is not None:
            if user_input["next_step"] == "add_patient":
                return await self.async_step_add_patient()
            elif user_input["next_step"] == "manage_patient":
                return await self.async_step_select_patient()

        return self.async_show_form(
            step_id="menu",
            data_schema=vol.Schema(
                {
                    vol.Required("next_step"): vol.In(
                        {
                            "add_patient": "Add New Patient",
                            "manage_patient": "Manage Existing Patient",
                        }
                    )
                }
            ),
        )

    async def async_step_add_patient(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding a new patient."""
        errors = {}

        if user_input is not None:
            coordinator = self.hass.data[DOMAIN].get("coordinator")
            if coordinator:
                try:
                    patient_id = await coordinator.add_patient(user_input)
                    if patient_id:
                        return await self.async_step_menu()
                except Exception as ex:
                    _LOGGER.exception("Error adding patient: %s", ex)
            errors["base"] = "add_failed"

        return self.async_show_form(
            step_id="add_patient",
            data_schema=ADD_PATIENT_SCHEMA,
            errors=errors,
        )

    async def async_step_select_patient(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select a patient to manage."""
        coordinator = self.hass.data[DOMAIN].get("coordinator")
        if not coordinator:
            return await self.async_step_menu()

        patients = coordinator.storage.get_patients()
        if not patients:
            return self.async_show_form(
                step_id="select_patient",
                errors={"base": "no_patients"},
            )

        if user_input is not None:
            self.selected_patient_id = user_input["patient_id"]
            return await self.async_step_patient_menu()

        return self.async_show_form(
            step_id="select_patient",
            data_schema=vol.Schema(
                {
                    vol.Required("patient_id"): vol.In(
                        {p["id"]: p["name"] for p in patients}
                    ),
                }
            ),
        )

    async def async_step_patient_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the patient management menu."""
        if user_input is not None:
            if user_input["action"] == "add_medication":
                return await self.async_step_add_medication()
            elif user_input["action"] == "remove_medication":
                return await self.async_step_select_medication()
            elif user_input["action"] == "back":
                return await self.async_step_menu()

        return self.async_show_form(
            step_id="patient_menu",
            data_schema=vol.Schema(
                {
                    vol.Required("action"): vol.In(
                        {
                            "add_medication": "Add Medication",
                            "remove_medication": "Remove Medication",
                            "back": "Back to Main Menu",
                        }
                    )
                }
            ),
        )

    async def async_step_select_medication(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select a medication to remove."""
        coordinator = self.hass.data[DOMAIN].get("coordinator")
        if not coordinator:
            return await self.async_step_patient_menu()

        # Get medications for current patient
        medications = [
            med for med_id, med in coordinator.storage.get_medications().items()
            if med.get("patient_id") == self.selected_patient_id
        ]
        
        if not medications:
            return self.async_show_form(
                step_id="select_medication",
                errors={"base": "no_medications"},
            )

        if user_input is not None:
            try:
                await coordinator.remove_medication(user_input["medication_id"])
                return await self.async_step_patient_menu()
            except Exception as ex:
                _LOGGER.exception("Error removing medication: %s", ex)
                return self.async_show_form(
                    step_id="select_medication",
                    errors={"base": "remove_failed"},
                )

        return self.async_show_form(
            step_id="select_medication",
            data_schema=vol.Schema(
                {
                    vol.Required("medication_id"): vol.In(
                        {m["id"]: m[ATTR_MEDICATION_NAME] for m in medications}
                    ),
                }
            ),
        ) 