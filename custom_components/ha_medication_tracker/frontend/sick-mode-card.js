/**
 * Sick Mode Card
 * A specialized card for displaying critical medication information during illness
 */

class SickModeCard extends HTMLElement {
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
    
    if (!config.patient_id) {
      throw new Error('Please specify a patient_id');
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

    // Get patient data
    const patientId = this._config.patient_id;
    const patientData = this._getPatientData(patientId);
    
    // Build the card content
    this.shadowRoot.innerHTML = `
      <ha-card>
        <div class="sick-mode-header">
          <div class="patient-info">
            <h2>${patientData.name || 'Patient'}</h2>
            ${this._renderLastTemperature(patientData)}
          </div>
          <div class="action-buttons">
            <mwc-button @click="${this._recordTemperature}">Record Temperature</mwc-button>
          </div>
        </div>
        <div class="card-content">
          <div class="section-header">Active Medications</div>
          ${this._renderActiveMedications(patientData)}
          
          <div class="section-header">Recent Temperature History</div>
          ${this._renderTemperatureHistory(patientData)}
          
          <div class="section-header">Medication Schedule</div>
          ${this._renderMedicationSchedule(patientData)}
        </div>
        <style>
          ha-card {
            overflow: hidden;
          }
          .sick-mode-header {
            background-color: var(--primary-color);
            color: var(--text-primary-color);
            padding: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
          }
          .patient-info h2 {
            margin: 0;
            font-size: 1.5em;
          }
          .temperature {
            font-size: 1.2em;
            font-weight: bold;
            margin-top: 4px;
          }
          .fever {
            color: var(--error-color, #ff5722);
          }
          .section-header {
            font-weight: bold;
            font-size: 1.1em;
            margin: 16px 0 8px 0;
            padding-bottom: 4px;
            border-bottom: 1px solid var(--divider-color);
          }
          .medication-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px;
            margin: 4px 0;
            border-radius: 4px;
            background-color: var(--secondary-background-color);
          }
          .medication-name {
            font-weight: bold;
          }
          .next-dose {
            white-space: nowrap;
          }
          .available-now {
            color: var(--success-color, #4caf50);
            font-weight: bold;
          }
          .upcoming {
            color: var(--warning-color, #ff9800);
          }
          .temperature-history {
            display: flex;
            overflow-x: auto;
            padding-bottom: 8px;
          }
          .temperature-point {
            min-width: 80px;
            text-align: center;
            padding: 8px 4px;
            margin: 0 4px;
            border-radius: 4px;
            background-color: var(--secondary-background-color);
          }
          .temp-value {
            font-weight: bold;
          }
          .temp-time {
            font-size: 0.8em;
            color: var(--secondary-text-color);
          }
          .medication-schedule {
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 8px;
          }
          .schedule-time {
            font-weight: bold;
          }
          .no-data {
            padding: 16px 8px;
            background-color: var(--secondary-background-color);
            border-radius: 4px;
            text-align: center;
            color: var(--secondary-text-color);
          }
          .toggle-button {
            display: flex;
            justify-content: center;
            margin-top: 8px;
          }
        </style>
      </ha-card>
    `;

    // Add event listeners
    this._addEventListeners();
  }

  // Get patient data
  _getPatientData(patientId) {
    // In a real implementation, this would fetch data from Home Assistant entities
    // For now, we'll return mock data
    return {
      id: patientId,
      name: 'Sample Patient',
      temperatures: [
        { value: 37.5, unit: '°C', timestamp: new Date(Date.now() - 3600000).toISOString() },
        { value: 38.2, unit: '°C', timestamp: new Date(Date.now() - 7200000).toISOString() },
        { value: 38.5, unit: '°C', timestamp: new Date(Date.now() - 10800000).toISOString() },
      ],
      medications: [
        { 
          id: 'med1', 
          name: 'Tylenol', 
          dosage: '10', 
          unit: 'mL',
          nextDose: { available_now: true, next_time: null }
        },
        { 
          id: 'med2', 
          name: 'Ibuprofen', 
          dosage: '5', 
          unit: 'mL',
          nextDose: { available_now: false, next_time: new Date(Date.now() + 3600000).toISOString() }
        }
      ],
      doses: [
        { medication_id: 'med1', timestamp: new Date(Date.now() - 7200000).toISOString() },
        { medication_id: 'med2', timestamp: new Date(Date.now() - 3600000).toISOString() }
      ]
    };
  }

  // Render the last temperature reading
  _renderLastTemperature(patientData) {
    if (!patientData.temperatures || patientData.temperatures.length === 0) {
      return `<div class="temperature">No temperature recorded</div>`;
    }

    // Get the most recent temperature
    const sortedTemps = [...patientData.temperatures].sort(
      (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
    );
    const lastTemp = sortedTemps[0];
    
    // Check if it's a fever (above 38°C or 100.4°F)
    const isFever = (lastTemp.unit === '°C' && lastTemp.value >= 38) || 
                    (lastTemp.unit === '°F' && lastTemp.value >= 100.4);
    
    return `
      <div class="temperature ${isFever ? 'fever' : ''}">
        ${lastTemp.value}${lastTemp.unit} 
        <span class="temp-time">
          ${this._formatTimeAgo(new Date(lastTemp.timestamp))}
        </span>
      </div>
    `;
  }

  // Render active medications section
  _renderActiveMedications(patientData) {
    if (!patientData.medications || patientData.medications.length === 0) {
      return `<div class="no-data">No active medications</div>`;
    }

    return patientData.medications.map(med => {
      let nextDoseText = '';
      
      if (med.nextDose.available_now) {
        nextDoseText = `<span class="available-now">Available now</span>`;
      } else if (med.nextDose.next_time) {
        const nextTime = new Date(med.nextDose.next_time);
        nextDoseText = `<span class="upcoming">
          Available ${this._formatTimeAgo(nextTime)}
        </span>`;
      }

      return `
        <div class="medication-item">
          <div>
            <div class="medication-name">${med.name}</div>
            <div class="medication-info">${med.dosage} ${med.unit}</div>
          </div>
          <div class="next-dose">
            ${nextDoseText}
            <mwc-button @click="${() => this._recordDose(med.id)}">
              Record Dose
            </mwc-button>
          </div>
        </div>
      `;
    }).join('');
  }

  // Render temperature history
  _renderTemperatureHistory(patientData) {
    if (!patientData.temperatures || patientData.temperatures.length < 2) {
      return `<div class="no-data">Not enough temperature data</div>`;
    }

    // Sort by timestamp descending and take the last 5
    const sortedTemps = [...patientData.temperatures]
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
      .slice(0, 5);
    
    return `
      <div class="temperature-history">
        ${sortedTemps.map(temp => {
          const tempTime = new Date(temp.timestamp);
          const isFever = (temp.unit === '°C' && temp.value >= 38) || 
                          (temp.unit === '°F' && temp.value >= 100.4);
          
          return `
            <div class="temperature-point">
              <div class="temp-value ${isFever ? 'fever' : ''}">
                ${temp.value}${temp.unit}
              </div>
              <div class="temp-time">
                ${tempTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  // Render medication schedule
  _renderMedicationSchedule(patientData) {
    if (!patientData.medications || patientData.medications.length === 0) {
      return `<div class="no-data">No medications scheduled</div>`;
    }

    // Create a schedule of upcoming doses
    const schedule = [];
    const now = new Date();
    
    patientData.medications.forEach(med => {
      if (med.nextDose.next_time) {
        const nextTime = new Date(med.nextDose.next_time);
        schedule.push({
          time: nextTime,
          medication: med.name,
          dosage: `${med.dosage} ${med.unit}`
        });
      }
    });
    
    // Sort by time
    schedule.sort((a, b) => a.time - b.time);
    
    if (schedule.length === 0) {
      return `<div class="no-data">All medications available now</div>`;
    }
    
    return `
      <div class="medication-schedule">
        ${schedule.map(item => `
          <div class="schedule-time">
            ${item.time.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
          </div>
          <div class="schedule-med">
            ${item.medication} (${item.dosage})
          </div>
        `).join('')}
      </div>
    `;
  }

  // Format time ago
  _formatTimeAgo(time) {
    const now = new Date();
    const diff = Math.floor((now - time) / 1000); // seconds
    
    if (diff < 0) {
      // Future time
      const minutes = Math.floor(-diff / 60);
      if (minutes < 60) {
        return `in ${minutes} min`;
      }
      const hours = Math.floor(minutes / 60);
      return `in ${hours} hr${hours > 1 ? 's' : ''}`;
    }
    
    if (diff < 60) {
      return 'just now';
    }
    
    const minutes = Math.floor(diff / 60);
    if (minutes < 60) {
      return `${minutes} min ago`;
    }
    
    const hours = Math.floor(minutes / 60);
    if (hours < 24) {
      return `${hours} hr${hours > 1 ? 's' : ''} ago`;
    }
    
    const days = Math.floor(hours / 24);
    return `${days} day${days > 1 ? 's' : ''} ago`;
  }

  // Add event listeners to the card elements
  _addEventListeners() {
    const recordTempBtn = this.shadowRoot.querySelector('.action-buttons mwc-button');
    if (recordTempBtn) {
      recordTempBtn.addEventListener('click', () => this._recordTemperature());
    }
  }

  // Record temperature handler
  _recordTemperature() {
    console.log('Record temperature clicked for patient', this._config.patient_id);
    // In a real implementation, this would show a dialog to record a temperature
  }

  // Record dose handler
  _recordDose(medicationId) {
    console.log('Record dose clicked for medication', medicationId);
    // In a real implementation, this would show a dialog to record a dose
  }
}

// Define the custom element
customElements.define('sick-mode-card', SickModeCard);

// Configure card type
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'sick-mode-card',
  name: 'Sick Mode Card',
  description: 'A card for displaying critical medication information during illness'
}); 