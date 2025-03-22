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

    // Get medication data
    const data = this._getMedicationData();

    // Build the card content
    this.shadowRoot.innerHTML = `
      <ha-card header="${this._config.title || 'Medication Tracker'}">
        <div class="card-content">
          ${this._renderPatients(data)}
        </div>
        <div class="card-actions">
          <mwc-button @click="${this._addPatient}">Add Patient</mwc-button>
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
        </style>
      </ha-card>
    `;

    // Add event listeners
    this._addEventListeners();
  }

  // Fetch medication data from Home Assistant
  _getMedicationData() {
    // In a real implementation, we would extract data from entities
    // For now, we'll return a mock structure
    return {
      patients: [],
      medications: [],
      doses: {},
      next_doses: {}
    };
  }

  // Render patient sections
  _renderPatients(data) {
    if (!data.patients || data.patients.length === 0) {
      return `
        <div class="empty-state">
          <p>No patients added yet. Click "Add Patient" to get started.</p>
        </div>
      `;
    }

    return data.patients.map(patient => `
      <div class="patient-section">
        <div class="patient-header">
          <span class="patient-name">${patient.name}</span>
          <div>
            <mwc-button @click="${() => this._addMedication(patient.id)}">Add Medication</mwc-button>
            <mwc-button @click="${() => this._recordTemperature(patient.id)}">Record Temperature</mwc-button>
          </div>
        </div>
        ${this._renderMedications(data, patient)}
      </div>
    `).join('');
  }

  // Render medications for a patient
  _renderMedications(data, patient) {
    const patientMeds = data.medications.filter(med => med.patient_id === patient.id);
    
    if (patientMeds.length === 0) {
      return `<p>No medications added for this patient.</p>`;
    }

    return patientMeds.map(med => {
      const nextDose = data.next_doses[med.id] || {};
      let doseStatus = '';
      
      if (nextDose.available_now) {
        doseStatus = `<span class="dose-available">Available now</span>`;
      } else if (nextDose.next_time) {
        const nextTime = new Date(nextDose.next_time);
        doseStatus = `<span class="dose-upcoming">Next dose available at ${nextTime.toLocaleTimeString()}</span>`;
      }

      return `
        <div class="medication-item">
          <div class="medication-name">${med.name}</div>
          <div class="medication-info">
            ${med.dosage ? `${med.dosage} ${med.unit || 'mg'}` : ''}
            ${med.instructions ? ` - ${med.instructions}` : ''}
          </div>
          <div>${doseStatus}</div>
          <div class="medication-buttons">
            <mwc-button @click="${() => this._recordDose(med.id)}">Record Dose</mwc-button>
          </div>
        </div>
      `;
    }).join('');
  }

  // Add event listeners to the card elements
  _addEventListeners() {
    // Add patient button
    const addPatientBtn = this.shadowRoot.querySelector('mwc-button');
    if (addPatientBtn) {
      addPatientBtn.addEventListener('click', () => this._addPatient());
    }
  }

  // Handle add patient action
  _addPatient() {
    // In a real implementation, this would show a dialog to add a patient
    console.log('Add patient clicked');
  }

  // Handle add medication action
  _addMedication(patientId) {
    // In a real implementation, this would show a dialog to add a medication
    console.log('Add medication clicked for patient', patientId);
  }

  // Handle record dose action
  _recordDose(medicationId) {
    // In a real implementation, this would show a dialog to record a dose
    console.log('Record dose clicked for medication', medicationId);
  }

  // Handle record temperature action
  _recordTemperature(patientId) {
    // In a real implementation, this would show a dialog to record a temperature
    console.log('Record temperature clicked for patient', patientId);
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