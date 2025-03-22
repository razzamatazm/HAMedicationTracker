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


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Medication Tracker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(
                title=user_input["name"],
                data=user_input,
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
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
        self.patient_data = {}
        self.medication_data = {}
        self.selected_patient_id = None
        self.selected_medication_id = None

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
            elif user_input["next_step"] == "add_medication":
                return await self.async_step_add_medication()
            elif user_input["next_step"] == "manage_medications":
                return await self.async_step_select_patient()

        return self.async_show_form(
            step_id="menu",
            data_schema=vol.Schema(
                {
                    vol.Required("next_step"): vol.In(
                        {
                            "add_patient": "Add Patient",
                            "add_medication": "Add Medication",
                            "manage_medications": "Manage Existing Medications",
                        }
                    )
                }
            ),
        )

    async def async_step_add_patient(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding a patient."""
        errors: dict[str, str] = {}

        if user_input is not None:
            coordinator = self.hass.data[DOMAIN].get("coordinator")
            if coordinator:
                patient_id = await coordinator.add_patient(user_input)
                if patient_id:
                    return await self.async_step_menu()
            errors["base"] = "add_failed"

        return self.async_show_form(
            step_id="add_patient",
            data_schema=ADD_PATIENT_SCHEMA,
            errors=errors,
        )

    async def async_step_add_medication(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding a medication."""
        errors: dict[str, str] = {}

        coordinator = self.hass.data[DOMAIN].get("coordinator")
        if not coordinator:
            return await self.async_step_menu()

        patients = coordinator.storage.get_patients()
        if not patients:
            errors["base"] = "no_patients"
            return self.async_show_form(
                step_id="add_medication",
                errors=errors,
                description_placeholders={
                    "error": "Please add a patient first"
                },
            )

        if user_input is not None:
            medication_data = {**user_input}
            if await coordinator.add_medication(medication_data):
                return await self.async_step_menu()
            errors["base"] = "add_failed"

        schema = {
            vol.Required("patient_id"): vol.In(
                {p["id"]: p["name"] for p in patients}
            ),
            **ADD_MEDICATION_SCHEMA.schema
        }

        return self.async_show_form(
            step_id="add_medication",
            data_schema=vol.Schema(schema),
            errors=errors,
        )

    async def async_step_select_patient(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select a patient to manage medications for."""
        coordinator = self.hass.data[DOMAIN].get("coordinator")
        if not coordinator:
            return await self.async_step_menu()

        patients = coordinator.storage.get_patients()
        if not patients:
            return await self.async_step_menu()

        if user_input is not None:
            self.selected_patient_id = user_input["patient_id"]
            return await self.async_step_manage_medications()

        return self.async_show_form(
            step_id="select_patient",
            data_schema=vol.Schema({
                vol.Required("patient_id"): vol.In(
                    {p["id"]: p["name"] for p in patients}
                ),
            }),
        )

    async def async_step_manage_medications(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage medications for the selected patient."""
        coordinator = self.hass.data[DOMAIN].get("coordinator")
        if not coordinator or not self.selected_patient_id:
            return await self.async_step_menu()

        medications = coordinator.storage.get_medications_for_patient(self.selected_patient_id)
        
        if user_input is not None:
            if user_input["action"] == "add":
                return await self.async_step_add_medication()
            elif user_input["action"] == "remove":
                self.selected_medication_id = user_input.get("medication_id")
                return await self.async_step_remove_medication()
            elif user_input["action"] == "back":
                return await self.async_step_menu()

        actions = {
            "add": "Add New Medication",
            "back": "Back to Menu",
        }

        schema = {
            vol.Required("action"): vol.In(actions),
        }

        if medications:
            actions["remove"] = "Remove Medication"
            schema[vol.Optional("medication_id")] = vol.In(
                {m["id"]: m["name"] for m in medications}
            )

        return self.async_show_form(
            step_id="manage_medications",
            data_schema=vol.Schema(schema),
        )

    async def async_step_remove_medication(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm and remove a medication."""
        if user_input is not None:
            if user_input.get("confirm"):
                coordinator = self.hass.data[DOMAIN].get("coordinator")
                if coordinator and self.selected_medication_id:
                    await coordinator.remove_medication(self.selected_medication_id)
            return await self.async_step_manage_medications()

        return self.async_show_form(
            step_id="remove_medication",
            data_schema=vol.Schema({
                vol.Required("confirm"): bool,
            }),
            description_placeholders={
                "medication": "selected medication"  # You could get the actual name here
            },
        ) 