/** RRC Agent Chat — Client-side logic */

const API_BASE = '';
let sessionId = null;
let conversationDone = false;

const messagesEl = document.getElementById('chat-messages');
const inputEl = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const typingEl = document.getElementById('typing-indicator');
const containerEl = document.getElementById('chat-container');

// ---------------------------------------------------------------------------
// Field-to-widget mapping
// ---------------------------------------------------------------------------

const FIELD_WIDGETS = {
  date_of_birth: { type: 'date' },
  height_feet: { type: 'number', attrs: { min: 3, max: 8, placeholder: 'Feet' } },
  height_inches: { type: 'number', attrs: { min: 0, max: 11, placeholder: 'Inches' } },
  weight_lbs: { type: 'number', attrs: { min: 50, max: 600, placeholder: 'Pounds' } },
  zip_code: { type: 'text', attrs: { pattern: '\\d{5}', maxlength: 5, placeholder: '00000' } },
  age: { type: 'number', attrs: { min: 18, max: 120 } },
  cigarettes_per_day: { type: 'number', attrs: { min: 0, max: 100 } },
  cigarette_years_smoked: { type: 'number', attrs: { min: 0, max: 80 } },
};

// Options for select-type fields
const FIELD_OPTIONS = {
  gender: ['Male', 'Female', 'Non-binary', 'Prefer not to say'],
  has_smartphone: ['Yes', 'No'],
  closest_rrc_site: ['Raleigh', 'Charlotte'],
  pregnant_or_nursing_or_planning: ['Yes', 'No'],
  willing_urine_drug_screen: ['Yes', 'No'],
};

// ---------------------------------------------------------------------------
// Start session
// ---------------------------------------------------------------------------

async function startSession() {
  try {
    const resp = await fetch(`${API_BASE}/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ study_id: 'zyn' }),
    });
    const data = await resp.json();
    sessionId = data.session_id;
    renderResponse(data);
  } catch (err) {
    addMessage('assistant', 'Unable to connect to the server. Please try again later.');
  }
}

// ---------------------------------------------------------------------------
// Send message
// ---------------------------------------------------------------------------

async function sendMessage(text) {
  if (!sessionId || conversationDone || !text.trim()) return;

  addMessage('user', text);
  inputEl.value = '';
  setInputEnabled(false);
  showTyping(true);

  try {
    const resp = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message: text }),
    });
    const data = await resp.json();
    showTyping(false);
    renderResponse(data);
  } catch (err) {
    showTyping(false);
    addMessage('assistant', 'Something went wrong. Please try again.');
    setInputEnabled(true);
  }
}

// ---------------------------------------------------------------------------
// Render agent response
// ---------------------------------------------------------------------------

function renderResponse(data) {
  if (data.type === 'form' && data.fields && data.fields.length > 0) {
    addMultiFieldForm(data.message, data.fields);
  } else if (data.type === 'form' && (data.field || data.options)) {
    addFormMessage(data.message, data.field, data.options);
  } else {
    addMessage('assistant', data.message);
  }

  if (data.done) {
    conversationDone = true;
    containerEl.classList.add('chat-ended');
    setInputEnabled(false);
  } else {
    setInputEnabled(true);
  }
}

// ---------------------------------------------------------------------------
// DOM helpers
// ---------------------------------------------------------------------------

function addMessage(role, text) {
  const div = document.createElement('div');
  div.className = `message message-${role}`;
  div.textContent = text;
  messagesEl.appendChild(div);
  scrollToBottom();
}

function addFormMessage(text, field, options) {
  const bubble = document.createElement('div');
  bubble.className = 'message message-assistant';

  const textP = document.createElement('p');
  textP.textContent = text;
  bubble.appendChild(textP);

  const form = document.createElement('div');
  form.className = 'form-widget';

  if (options && options.length > 0) {
    // Radio buttons
    const radioGroup = document.createElement('div');
    radioGroup.className = 'radio-group';
    options.forEach((opt) => {
      const label = document.createElement('label');
      label.className = 'radio-option';
      const radio = document.createElement('input');
      radio.type = 'radio';
      radio.name = `field-${field || 'choice'}`;
      radio.value = opt;
      label.appendChild(radio);
      label.appendChild(document.createTextNode(opt));
      radioGroup.appendChild(label);
    });
    form.appendChild(radioGroup);

    const submitBtn = document.createElement('button');
    submitBtn.className = 'form-submit';
    submitBtn.textContent = 'Submit';
    submitBtn.onclick = () => {
      const selected = form.querySelector('input[type="radio"]:checked');
      if (selected) {
        submitBtn.disabled = true;
        disableFormInputs(form);
        sendMessage(selected.value);
      }
    };
    form.appendChild(submitBtn);
  } else if (field) {
    // Input field
    const config = FIELD_WIDGETS[field] || { type: 'text' };
    const input = document.createElement('input');
    input.type = config.type || 'text';
    if (config.attrs) {
      Object.entries(config.attrs).forEach(([k, v]) => input.setAttribute(k, v));
    }
    if (!input.getAttribute('placeholder')) {
      input.placeholder = `Enter your ${field.replace(/_/g, ' ')}`;
    }
    form.appendChild(input);

    const submitBtn = document.createElement('button');
    submitBtn.className = 'form-submit';
    submitBtn.textContent = 'Submit';
    submitBtn.onclick = () => {
      if (input.value.trim()) {
        submitBtn.disabled = true;
        disableFormInputs(form);
        sendMessage(input.value.trim());
      }
    };
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') submitBtn.click();
    });
    form.appendChild(submitBtn);
  }

  bubble.appendChild(form);
  messagesEl.appendChild(bubble);
  scrollToBottom();
}

function createFieldInput(f) {
  const options = FIELD_OPTIONS[f.name];
  const widgetConfig = FIELD_WIDGETS[f.name];

  // Multi-select checkbox group
  if (f.type === 'multi_select' && f.options && f.options.length > 0) {
    const group = document.createElement('div');
    group.className = 'checkbox-group';
    group.dataset.name = f.name;
    f.options.forEach((opt) => {
      const label = document.createElement('label');
      label.className = 'checkbox-option';
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.name = f.name;
      cb.value = opt;
      label.appendChild(cb);
      label.appendChild(document.createTextNode(opt));
      group.appendChild(label);
    });
    return group;
  }

  // Select dropdown
  if (f.type === 'select' || options) {
    const select = document.createElement('select');
    select.name = f.name;
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = `Select...`;
    placeholder.disabled = true;
    placeholder.selected = true;
    select.appendChild(placeholder);
    (options || []).forEach((opt) => {
      const option = document.createElement('option');
      option.value = opt;
      option.textContent = opt;
      select.appendChild(option);
    });
    return select;
  }

  // Regular input
  const input = document.createElement('input');
  if (widgetConfig) {
    input.type = widgetConfig.type || f.type || 'text';
    if (widgetConfig.attrs) {
      Object.entries(widgetConfig.attrs).forEach(([k, v]) => input.setAttribute(k, v));
    }
  } else {
    input.type = f.type || 'text';
  }
  input.name = f.name;
  if (!input.getAttribute('placeholder')) {
    input.placeholder = f.label;
  }
  input.autocomplete = f.name === 'email' ? 'email' : f.name === 'phone' ? 'tel' : 'off';
  return input;
}

function addMultiFieldForm(text, fields) {
  const bubble = document.createElement('div');
  bubble.className = 'message message-assistant';

  const textP = document.createElement('p');
  textP.textContent = text;
  bubble.appendChild(textP);

  const form = document.createElement('div');
  form.className = 'form-widget';

  const inputs = {};
  fields.forEach((f) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'form-field-group';

    const label = document.createElement('label');
    label.className = 'form-field-label';
    label.textContent = f.label;
    wrapper.appendChild(label);

    const input = createFieldInput(f);
    wrapper.appendChild(input);

    form.appendChild(wrapper);
    inputs[f.name] = input;
  });

  const submitBtn = document.createElement('button');
  submitBtn.className = 'form-submit';
  submitBtn.textContent = 'Submit';
  submitBtn.onclick = () => {
    // Build payload — checkbox groups produce arrays, others produce strings
    const data = {};
    let allFilled = true;
    Object.entries(inputs).forEach(([name, el]) => {
      if (el.classList && el.classList.contains('checkbox-group')) {
        const checked = Array.from(el.querySelectorAll('input[type="checkbox"]:checked'))
          .map((cb) => cb.value);
        if (checked.length === 0) allFilled = false;
        data[name] = checked;
      } else {
        if (!el.value || !el.value.trim()) allFilled = false;
        else data[name] = el.value.trim();
      }
    });
    if (!allFilled) return;

    submitBtn.disabled = true;
    disableFormInputs(form);
    sendMessage(JSON.stringify(data));
  };

  // Allow Enter on last non-select field to submit
  const fieldList = Object.values(inputs);
  const lastInput = fieldList[fieldList.length - 1];
  if (lastInput.tagName !== 'SELECT') {
    lastInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') submitBtn.click();
    });
  }

  form.appendChild(submitBtn);
  bubble.appendChild(form);
  messagesEl.appendChild(bubble);
  scrollToBottom();

  // Focus first input
  fieldList[0].focus();
}

function disableFormInputs(form) {
  form.querySelectorAll('input, button, select').forEach((el) => {
    el.disabled = true;
  });
}

function showTyping(visible) {
  typingEl.classList.toggle('visible', visible);
  scrollToBottom();
}

function setInputEnabled(enabled) {
  inputEl.disabled = !enabled;
  sendBtn.disabled = !enabled;
  if (enabled) inputEl.focus();
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ---------------------------------------------------------------------------
// Event listeners
// ---------------------------------------------------------------------------

sendBtn.addEventListener('click', () => sendMessage(inputEl.value));
inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage(inputEl.value);
  }
});

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

startSession();
