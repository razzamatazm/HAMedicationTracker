/**
 * Medication Tracker Card
 * Custom card for displaying medication tracking information
 */

class MedicationTrackerCard extends HTMLElement {
  constructor() {
    super();
    this._config = {};
    this._hass = null;
  }

  // Set the configuration
  setConfig(config) {
    if (!config) {
      throw new Error('Invalid configuration');
    }
    this._config = config;
  }

  // Get the card size
  getCardSize() {
    return 3;
  }

  // Set the Home Assistant instance
  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  // Render the card
  _render() {
    if (!this._hass || !this._config) {
      return;
    }

    if (!this.shadowRoot) {
      this.attachShadow({ mode: 'open' });
    }

    // Get medication data from entities
    const data = this._getMedicationData();

    // Build the card content
    this.shadowRoot.innerHTML = `
      <ha-card header="${this._config.title || 'Medication Tracker'}">
        <div class="card-content">
          ${this._renderPatients(data)}
        </div>
        <div class="card-actions">
          <mwc-button @click="${this._openHAConfig}">Manage Patients & Medications</mwc-button>
        </div>
        <style>
          .medication-card {
            padding: 16px;
          }
          .patient-section {
            margin-bottom: 16px;
            padding: 8px;
            border-radius: 4px;
            background-color: var(--card-background-color, #fff);
            box-shadow: 0 2px 2px rgba(0, 0, 0, 0.1);
          }
          .patient-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
            border-bottom: 1px solid var(--divider-color, #e0e0e0);
            padding-bottom: 8px;
          }
          .patient-name {
            font-weight: bold;
            font-size: 1.1em;
          }
          .medication-item {
            margin: 4px 0;
            padding: 4px 8px;
            border-radius: 4px;
            background-color: var(--secondary-background-color, #f5f5f5);
          }
          .medication-name {
            font-weight: bold;
          }
          .medication-info {
            font-size: 0.9em;
            color: var(--secondary-text-color, #757575);
          }
          .dose-warning {
            color: var(--error-color, #db4437);
          }
          .dose-available {
            color: var(--success-color, #43a047);
          }
          .dose-upcoming {
            color: var(--warning-color, #ffa600);
          }
          .medication-buttons {
            display: flex;
            justify-content: flex-end;
            margin-top: 4px;
          }
          mwc-button {
            --mdc-theme-primary: var(--primary-color);
          }
          .empty-state {
            padding: 16px;
            text-align: center;
            color: var(--secondary-text-color, #757575);
          }
          .temperature-info {
            font-size: 0.9em;
            margin-top: 4px;
          }
          .fever {
            color: var(--error-color, #db4437);
          }
        </style>
      </ha-card>
    `;

    // Add event listeners
    this._addEventListeners();
  }

  // Get medication data from Home Assistant entities
  _getMedicationData() {
    const data = {
      patients: [],
      medications: {},
      doses: {},
      next_doses: {},
      temperatures: {}
    };

    // Find all patient sensors
    Object.keys(this._hass.states).forEach(entityId => {
      if (entityId.startsWith('sensor.medication_tracker_patient_')) {
        const state = this._hass.states[entityId];
        if (state) {
          const patient = {
            id: state.attributes.id,
            name: state.state,
            weight: state.attributes.weight,
            weight_unit: state.attributes.weight_unit,
            age: state.attributes.age,
            last_temperature: state.attributes.last_temperature,
            last_temperature_unit: state.attributes.last_temperature_unit,
            last_temperature_time: state.attributes.last_temperature_time
          };
          data.patients.push(patient);
        }
      }
    });

    // Find all medication sensors
    Object.keys(this._hass.states).forEach(entityId => {
      if (entityId.startsWith('sensor.medication_tracker_medication_')) {
        const state = this._hass.states[entityId];
        if (state) {
          const medication = {
            id: state.attributes.id,
            name: state.attributes.name,
            patient_id: state.attributes.patient_id,
            dosage: state.attributes.dosage,
            unit: state.attributes.unit,
            frequency: state.attributes.frequency,
            instructions: state.attributes.instructions,
            available_now: state.attributes.available_now,
            next_dose_time: state.attributes.next_dose_time,
            last_dose_time: state.attributes.last_dose_time,
            last_dose_amount: state.attributes.last_dose_amount,
            last_dose_unit: state.attributes.last_dose_unit
          };
          data.medications[medication.id] = medication;
        }
      }
    });

    return data;
  }

  // Render patient sections
  _renderPatients(data) {
    if (!data.patients || data.patients.length === 0) {
      return `
        <div class="empty-state">
          <p>No patients added yet. Click "Manage Patients & Medications" to get started.</p>
        </div>
      `;
    }

    return data.patients.map(patient => `
      <div class="patient-section">
        <div class="patient-header">
          <div>
            <span class="patient-name">${patient.name}</span>
            ${this._renderTemperatureInfo(patient)}
          </div>
          <div>
            <mwc-button @click="${() => this._recordTemperature(patient.id)}">Record Temperature</mwc-button>
          </div>
        </div>
        ${this._renderMedications(data, patient)}
      </div>
    `).join('');
  }

  // Render temperature information
  _renderTemperatureInfo(patient) {
    if (!patient.last_temperature) {
      return '';
    }

    const isFever = (patient.last_temperature_unit === '°C' && patient.last_temperature >= 38) ||
                   (patient.last_temperature_unit === '°F' && patient.last_temperature >= 100.4);

    return `
      <div class="temperature-info ${isFever ? 'fever' : ''}">
        Temperature: ${patient.last_temperature}${patient.last_temperature_unit}
        ${patient.last_temperature_time ? `(${this._formatTimeAgo(new Date(patient.last_temperature_time))})` : ''}
      </div>
    `;
  }

  // Render medications for a patient
  _renderMedications(data, patient) {
    const patientMeds = Object.values(data.medications)
      .filter(med => med.patient_id === patient.id);
    
    if (patientMeds.length === 0) {
      return `<p>No medications added for this patient.</p>`;
    }

    return patientMeds.map(med => {
      let doseStatus = '';
      
      if (med.available_now) {
        doseStatus = `<span class="dose-available">Available now</span>`;
      } else if (med.next_dose_time) {
        doseStatus = `<span class="dose-upcoming">Next dose at ${this._formatTime(new Date(med.next_dose_time))}</span>`;
      }

      return `
        <div class="medication-item">
          <div class="medication-name">${med.name}</div>
          <div class="medication-info">
            ${med.dosage ? `${med.dosage} ${med.unit}` : ''}
            ${med.instructions ? ` - ${med.instructions}` : ''}
          </div>
          <div>${doseStatus}</div>
          ${med.last_dose_time ? `
            <div class="medication-info">
              Last dose: ${med.last_dose_amount} ${med.last_dose_unit} 
              (${this._formatTimeAgo(new Date(med.last_dose_time))})
            </div>
          ` : ''}
          <div class="medication-buttons">
            <mwc-button @click="${() => this._recordDose(med.id)}">Record Dose</mwc-button>
          </div>
        </div>
      `;
    }).join('');
  }

  // Format time ago
  _formatTimeAgo(time) {
    const now = new Date();
    const diff = Math.floor((now - time) / 1000); // seconds
    
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  }

  // Format time
  _formatTime(date) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  // Add event listeners to the card elements
  _addEventListeners() {
    const configBtn = this.shadowRoot.querySelector('.card-actions mwc-button');
    if (configBtn) {
      configBtn.addEventListener('click', () => this._openHAConfig());
    }

    // Add event listeners for all record dose buttons
    this.shadowRoot.querySelectorAll('.medication-buttons mwc-button').forEach(btn => {
      const medicationId = btn.getAttribute('data-medication-id');
      if (medicationId) {
        btn.addEventListener('click', () => this._recordDose(medicationId));
      }
    });

    // Add event listeners for all record temperature buttons
    this.shadowRoot.querySelectorAll('.patient-header mwc-button').forEach(btn => {
      const patientId = btn.getAttribute('data-patient-id');
      if (patientId) {
        btn.addEventListener('click', () => this._recordTemperature(patientId));
      }
    });
  }

  // Open Home Assistant configuration
  _openHAConfig() {
    if (this._hass) {
      this._hass.callService('ha_medication_tracker', 'open_config', {});
    }
  }

  // Record dose handler
  async _recordDose(medicationId) {
    if (!this._hass) return;

    // Create a dialog for dose recording
    const dialog = document.createElement('dialog');
    dialog.innerHTML = `
      <form method="dialog" style="
        display: flex;
        flex-direction: column;
        gap: 16px;
        min-width: 300px;
        padding: 16px;
      ">
        <h3 style="margin: 0;">Record Dose</h3>
        <div style="display: flex; flex-direction: column; gap: 8px;">
          <label for="dose-time">Time taken:</label>
          <input type="datetime-local" id="dose-time" 
            value="${new Date().toISOString().slice(0, 16)}" 
            max="${new Date().toISOString().slice(0, 16)}"
          />
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          <mwc-button dialogAction="cancel">Cancel</mwc-button>
          <mwc-button dialogAction="confirm" style="--mdc-theme-primary: var(--primary-color);">
            Record
          </mwc-button>
        </div>
      </form>
    `;

    // Add dialog to the shadow root
    this.shadowRoot.appendChild(dialog);

    // Show the dialog
    dialog.showModal();

    // Handle dialog close
    dialog.addEventListener('close', async (e) => {
      if (dialog.returnValue === 'confirm') {
        const timeInput = dialog.querySelector('#dose-time');
        const doseTime = new Date(timeInput.value);

        // Call the record_dose service with the selected time
        await this._hass.callService('ha_medication_tracker', 'record_dose', {
          medication_id: medicationId,
          timestamp: doseTime.toISOString(),
        });
      }
      
      // Remove the dialog
      dialog.remove();
    });
  }

  // Record temperature handler
  async _recordTemperature(patientId) {
    if (!this._hass) return;

    // Create a dialog for temperature recording
    const dialog = document.createElement('dialog');
    dialog.innerHTML = `
      <form method="dialog" style="
        display: flex;
        flex-direction: column;
        gap: 16px;
        min-width: 300px;
        padding: 16px;
      ">
        <h3 style="margin: 0;">Record Temperature</h3>
        <div style="display: flex; flex-direction: column; gap: 8px;">
          <label for="temp-value">Temperature:</label>
          <input type="number" id="temp-value" step="0.1" required
            style="padding: 8px; border: 1px solid var(--divider-color);"
          />
          <label for="temp-time">Time taken:</label>
          <input type="datetime-local" id="temp-time" 
            value="${new Date().toISOString().slice(0, 16)}"
            max="${new Date().toISOString().slice(0, 16)}"
          />
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 8px;">
          <mwc-button dialogAction="cancel">Cancel</mwc-button>
          <mwc-button dialogAction="confirm" style="--mdc-theme-primary: var(--primary-color);">
            Record
          </mwc-button>
        </div>
      </form>
    `;

    // Add dialog to the shadow root
    this.shadowRoot.appendChild(dialog);

    // Show the dialog
    dialog.showModal();

    // Handle dialog close
    dialog.addEventListener('close', async (e) => {
      if (dialog.returnValue === 'confirm') {
        const tempInput = dialog.querySelector('#temp-value');
        const timeInput = dialog.querySelector('#temp-time');
        
        const temp = parseFloat(tempInput.value);
        if (isNaN(temp)) {
          alert('Please enter a valid temperature');
          return;
        }

        const tempTime = new Date(timeInput.value);

        // Call the record_temperature service with the selected time
        await this._hass.callService('ha_medication_tracker', 'record_temperature', {
          patient_id: patientId,
          temperature_value: temp,
          timestamp: tempTime.toISOString(),
        });
      }
      
      // Remove the dialog
      dialog.remove();
    });
  }
}

// Define the custom element
customElements.define('medication-tracker-card', MedicationTrackerCard);

// Configure card type
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'medication-tracker-card',
  name: 'Medication Tracker Card',
  description: 'A card for tracking medications for multiple patients'
}); 