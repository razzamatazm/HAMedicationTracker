# Home Assistant Medication Tracker

A comprehensive medication tracking integration for Home Assistant that helps track medications for multiple people (especially children). Perfect for tracking pain/fever medications like Tylenol and ibuprofen during illness, but flexible enough for other scenarios.

## Features

- Track medications for multiple people (patients)
- Add medications with customizable properties (dosage, frequency, instructions)
- Track when doses were administered
- Calculate and display when next doses are available
- Track temperature readings alongside medication administration
- Dosage calculators for common children's medications based on weight
- Warning system for maximum daily doses
- Option for alternating medication schedules (Tylenol/ibuprofen rotation)
- "Sick Mode" dashboard for quick access to crucial information

## Installation

### HACS (Recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance
2. Add this repository to HACS as a custom repository:
   - Go to HACS > Integrations
   - Click the three dots in the upper right corner
   - Select "Custom repositories"
   - Add the URL of this repository and select "Integration" as the category
3. Click "Install" when the integration appears in HACS
4. Restart Home Assistant
5. Add the integration via the Home Assistant UI (Configuration > Integrations > Add Integration)

### Manual Installation

1. Download the latest release from the GitHub repository
2. Extract the contents to your Home Assistant configuration directory under `custom_components/ha_medication_tracker`
3. Restart Home Assistant
4. Add the integration via the Home Assistant UI (Configuration > Integrations > Add Integration)

## Configuration

The integration is configured through the Home Assistant UI. After installation, go to Configuration > Integrations and add the "Medication Tracker" integration.

## Usage

Once configured, you can:
- Add patients and their medications
- Log doses and temperature readings
- View medication schedules and next available doses
- Add the "Medication Tracker" or "Sick Mode" cards to your dashboard

## Documentation

For detailed documentation and examples, see the [Wiki](https://github.com/yourusername/HAMedicationTracker/wiki).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 