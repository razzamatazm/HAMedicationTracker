"""Constants for the Medication Tracker integration."""

DOMAIN = "ha_medication_tracker"

# Configuration and options
CONF_PATIENTS = "patients"
CONF_MEDICATIONS = "medications"
CONF_DOSES = "doses"
CONF_TEMPERATURES = "temperatures"

# Default configurations
DEFAULT_NAME = "Medication Tracker"

# Attributes
ATTR_PATIENT_ID = "patient_id"
ATTR_PATIENT_NAME = "patient_name"
ATTR_PATIENT_WEIGHT = "patient_weight"
ATTR_PATIENT_WEIGHT_UNIT = "patient_weight_unit" 
ATTR_PATIENT_AGE = "patient_age"
ATTR_MEDICATION_ID = "medication_id"
ATTR_MEDICATION_NAME = "medication_name"
ATTR_MEDICATION_DOSAGE = "medication_dosage"
ATTR_MEDICATION_UNIT = "medication_unit"
ATTR_MEDICATION_FREQUENCY = "medication_frequency"
ATTR_MEDICATION_MAX_DAILY_DOSES = "medication_max_daily_doses"
ATTR_MEDICATION_INSTRUCTIONS = "medication_instructions"
ATTR_DOSE_TIMESTAMP = "dose_timestamp"
ATTR_DOSE_AMOUNT = "dose_amount"
ATTR_DOSE_UNIT = "dose_unit"
ATTR_TEMPERATURE_TIMESTAMP = "temperature_timestamp"
ATTR_TEMPERATURE_VALUE = "temperature_value"
ATTR_TEMPERATURE_UNIT = "temperature_unit"
ATTR_NEXT_DOSE_TIME = "next_dose_time"

# Service names
SERVICE_ADD_PATIENT = "add_patient"
SERVICE_REMOVE_PATIENT = "remove_patient"
SERVICE_ADD_MEDICATION = "add_medication"
SERVICE_REMOVE_MEDICATION = "remove_medication"
SERVICE_RECORD_DOSE = "record_dose"
SERVICE_RECORD_TEMPERATURE = "record_temperature" 