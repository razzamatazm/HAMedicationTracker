/**
 * Medication Tracker Card
 * Custom card for displaying medication tracking information
 */

class MedicationTrackerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    if (!config.patient_id) {
      throw new Error('Please specify a patient_id');
    }
    this.config = config;
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  static getConfigElement() {
    return document.createElement('medication-tracker-card-editor');
  }

  static getStubConfig() {
    return { patient_id: '' };
  }

  render() {
    if (!this._hass || !this.config) return;

    const patientData = this._getPatientData();
    if (!patientData) {
      this.shadowRoot.innerHTML = `
        <ha-card>
          <div class="card-content">
            <div>Patient not found</div>
          </div>
        </ha-card>
      `;
      return;
    }

    const medicationData = this._getMedicationData();
    
    this.shadowRoot.innerHTML = `
      <ha-card>
        <style>
          .card-content {
            padding: 16px;
          }
          .header {
            font-size: 1.2em;
            font-weight: 500;
            margin-bottom: 16px;
          }
          .medication {
            margin-bottom: 16px;
            padding: 12px;
            border-radius: 4px;
            background: var(--primary-background-color);
          }
          .medication-name {
            font-weight: 500;
            margin-bottom: 8px;
          }
          .medication-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 8px;
          }
          .info-item {
            display: flex;
            flex-direction: column;
          }
          .info-label {
            font-size: 0.9em;
            color: var(--secondary-text-color);
          }
          .info-value {
            font-size: 1.1em;
          }
          .controls {
            display: flex;
            gap: 8px;
            margin-top: 8px;
          }
          ha-button {
            flex: 1;
          }
        </style>
        <div class="card-content">
          <div class="header">${patientData.name}'s Medications</div>
          ${Object.values(medicationData).map(med => this._renderMedication(med)).join('')}
        </div>
      </ha-card>
    `;

    // Add event listeners after rendering
    this.shadowRoot.querySelectorAll('.record-dose').forEach(button => {
      button.addEventListener('click', (e) => this._recordDose(e.target.dataset.medicationId));
    });
  }

  _renderMedication(medication) {
    const nextDose = this._hass.states[`sensor.next_dose_of_${medication.name.toLowerCase()}`];
    const lastDose = this._hass.states[`sensor.last_dose_of_${medication.name.toLowerCase()}`];
    const compliance = this._hass.states[`sensor.${medication.name.toLowerCase()}_compliance`];

    return `
      <div class="medication">
        <div class="medication-name">${medication.name}</div>
        <div class="medication-info">
          <div class="info-item">
            <span class="info-label">Dosage</span>
            <span class="info-value">${medication.dosage} ${medication.unit}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Next Dose</span>
            <span class="info-value">${nextDose ? nextDose.state : 'Unknown'}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Last Dose</span>
            <span class="info-value">${lastDose ? lastDose.state : 'Never'}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Compliance</span>
            <span class="info-value">${compliance ? compliance.state : '0'}%</span>
          </div>
        </div>
        <div class="controls">
          <ha-button
            class="record-dose"
            data-medication-id="${medication.id}"
          >
            Record Dose
          </ha-button>
        </div>
      </div>
    `;
  }

  _getPatientData() {
    const patientId = this.config.patient_id;
    const patientSensor = Object.values(this._hass.states).find(
      state => state.entity_id.startsWith('sensor.medication_tracker_patient_') &&
              state.attributes.id === patientId
    );
    return patientSensor ? {
      id: patientId,
      name: patientSensor.attributes.name || 'Unknown Patient',
      weight: patientSensor.attributes.weight,
      weight_unit: patientSensor.attributes.weight_unit,
      age: patientSensor.attributes.age,
    } : null;
  }

  _getMedicationData() {
    const patientId = this.config.patient_id;
    const medications = {};
    
    Object.values(this._hass.states).forEach(state => {
      if (state.entity_id.startsWith('sensor.medication_tracker_medication_') &&
          state.attributes.patient_id === patientId) {
        medications[state.attributes.id] = {
          id: state.attributes.id,
          name: state.attributes.name,
          dosage: state.attributes.dosage,
          unit: state.attributes.unit,
          frequency: state.attributes.frequency,
          instructions: state.attributes.instructions,
        };
      }
    });
    
    return medications;
  }

  async _recordDose(medicationId) {
    const medication = this._getMedicationData()[medicationId];
    if (!medication) return;

    await this._hass.callService('ha_medication_tracker', 'record_dose', {
      medication_id: medicationId,
      dose_amount: medication.dosage,
      dose_unit: medication.unit,
    });
  }

  getCardSize() {
    return 3;
  }
}

customElements.define('medication-tracker-card', MedicationTrackerCard);

// Configure card type
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'medication-tracker-card',
  name: 'Medication Tracker Card',
  description: 'A card for tracking medications for multiple patients'
}); 