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

# Schema for the initial configuration
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("name", default=DEFAULT_NAME): str,
    }
)

# Schema for adding a patient
ADD_PATIENT_SCHEMA = vol.Schema(
    {
        vol.Required("name"): str,
        vol.Optional("weight"): vol.Coerce(float),
        vol.Optional("weight_unit", default="kg"): vol.In(["kg", "lb"]),
        vol.Optional("age"): vol.Coerce(int),
    }
)

# Schema for adding a medication
ADD_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required("name"): str,
        vol.Optional("dosage"): vol.Coerce(float),
        vol.Optional("unit", default="mg"): str,
        vol.Optional("frequency", default=6): vol.Coerce(float),
        vol.Optional("instructions"): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Medication Tracker."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.patients = []
        self.current_patient = None
        self.name = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            # Store the name and proceed to patient setup
            self.name = user_input["name"]
            return await self.async_step_add_patients()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
        )

    async def async_step_add_patients(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding patients."""
        errors = {}

        if user_input is not None:
            if user_input.get("done"):
                if not self.patients:
                    errors["base"] = "no_patients"
                else:
                    # All patients added, create the config entry
                    return self.async_create_entry(
                        title=self.name,
                        data={
                            "name": self.name,
                            "patients": self.patients,
                        },
                    )
            else:
                try:
                    # Add the patient to our list
                    patient_id = str(uuid.uuid4())
                    patient_data = {
                        "id": patient_id,
                        "name": user_input["name"],
                        "weight": user_input.get("weight"),
                        "weight_unit": user_input.get("weight_unit", "kg"),
                        "age": user_input.get("age"),
                        "medications": [],
                    }
                    self.patients.append(patient_data)
                    # Move to medication setup for this patient
                    self.current_patient = patient_data
                    return await self.async_step_add_medications()
                except Exception as ex:
                    _LOGGER.exception("Error adding patient: %s", ex)
                    errors["base"] = "add_failed"

        schema = ADD_PATIENT_SCHEMA.extend(
            {
                vol.Optional("done", default=False): bool,
            }
        )

        return self.async_show_form(
            step_id="add_patients",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "patient_count": str(len(self.patients)),
                "patient_list": ", ".join(p["name"] for p in self.patients),
            },
        )

    async def async_step_add_medications(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding medications for the current patient."""
        errors = {}

        if user_input is not None:
            if user_input.get("done"):
                # Done adding medications for this patient
                return await self.async_step_add_patients()
            else:
                try:
                    # Add the medication to the current patient
                    medication_id = str(uuid.uuid4())
                    medication_data = {
                        "id": medication_id,
                        "patient_id": self.current_patient["id"],
                        "name": user_input["name"],
                        "dosage": user_input.get("dosage"),
                        "unit": user_input.get("unit", "mg"),
                        "frequency": user_input.get("frequency", 6),
                        "instructions": user_input.get("instructions"),
                    }
                    self.current_patient["medications"].append(medication_data)
                    # Stay on this step to add more medications
                    return await self.async_step_add_medications()
                except Exception as ex:
                    _LOGGER.exception("Error adding medication: %s", ex)
                    errors["base"] = "add_failed"

        # Create a conditional schema based on whether we're adding a medication or marking as done
        base_schema = {
            vol.Optional("done", default=False): bool,
        }

        medication_schema = {
            vol.Required("name"): str,
            vol.Optional("dosage"): vol.Coerce(float),
            vol.Optional("unit", default="mg"): str,
            vol.Optional("frequency", default=6): vol.Coerce(float),
            vol.Optional("instructions"): str,
        }

        schema = vol.Schema(base_schema).extend(
            medication_schema if not (user_input and user_input.get("done")) else {}
        )

        return self.async_show_form(
            step_id="add_medications",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "patient_name": self.current_patient["name"],
                "medication_count": str(len(self.current_patient["medications"])),
                "medication_list": ", ".join(
                    m["name"] for m in self.current_patient["medications"]
                ),
            },
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

    async def async_step_add_medication(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a medication to the selected patient."""
        errors = {}

        if user_input is not None:
            coordinator = self.hass.data[DOMAIN].get("coordinator")
            if coordinator:
                try:
                    medication_data = {
                        "patient_id": self.selected_patient_id,
                        **user_input,
                    }
                    if await coordinator.add_medication(medication_data):
                        return await self.async_step_patient_menu()
                except Exception as ex:
                    _LOGGER.exception("Error adding medication: %s", ex)
            errors["base"] = "add_failed"

        return self.async_show_form(
            step_id="add_medication",
            data_schema=ADD_MEDICATION_SCHEMA,
            errors=errors,
        )

    async def async_step_select_medication(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select a medication to remove."""
        coordinator = self.hass.data[DOMAIN].get("coordinator")
        if not coordinator:
            return await self.async_step_patient_menu()

        medications = coordinator.storage.get_medications_for_patient(self.selected_patient_id)
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
                        {m["id"]: m["name"] for m in medications}
                    ),
                }
            ),
        ) 