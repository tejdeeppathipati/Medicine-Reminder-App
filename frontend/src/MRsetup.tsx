import { useState, type FormEvent } from "react";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:5001";
const FREQS = ["Daily", "Twice daily", "Weekly", "As needed"];
const NOTIFY_OPTIONS = ["On missed dose", "Daily summary", "Both"];
const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

interface Medicine {
  name: string;
  dosage: string;
  time: string;
  secondTime: string;
  frequency: string;
  weeklyDay: string;
}

interface Caregiver {
  name: string;
  phone: string;
}

const emptyMedicine = (): Medicine => ({
  name: "",
  dosage: "",
  time: "",
  secondTime: "",
  frequency: FREQS[0],
  weeklyDay: WEEKDAYS[0],
});

export default function MedicineSetup() {
  const [patient, setPatient] = useState({ name: "", phone: "" });
  const [medicines, setMedicines] = useState<Medicine[]>([emptyMedicine()]);
  const [caregiver, setCaregiver] = useState<Caregiver>({ name: "", phone: "" });
  const [notifyWhen, setNotifyWhen] = useState(NOTIFY_OPTIONS[0]);
  const [toast, setToast] = useState("");
  const [toastVisible, setToastVisible] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const showToast = (message: string) => {
    setToast(message);
    setToastVisible(true);
    window.setTimeout(() => setToastVisible(false), 2600);
  };

  const updateMedicine = (
    index: number,
    field: keyof Medicine,
    value: string
  ) => {
    setMedicines((current) =>
      current.map((medicine, medicineIndex) =>
        medicineIndex === index ? { ...medicine, [field]: value } : medicine
      )
    );
  };

  const addMedicine = () => {
    setMedicines((current) => [...current, emptyMedicine()]);
  };

  const removeMedicine = (index: number) => {
    setMedicines((current) =>
      current.filter((_, medicineIndex) => medicineIndex !== index)
    );
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!patient.name.trim() || !patient.phone.trim()) {
      showToast("Add the patient name and phone");
      return;
    }

    if (medicines.length === 0) {
      showToast("Add at least one medicine");
      return;
    }

    const incompleteMedicine = medicines.some((medicine) => {
      if (!medicine.name.trim() || !medicine.dosage.trim()) {
        return true;
      }
      if (medicine.frequency === "As needed") {
        return false;
      }
      if (!medicine.time.trim()) {
        return true;
      }
      return medicine.frequency === "Twice daily" && !medicine.secondTime.trim();
    });

    if (incompleteMedicine) {
      showToast("Complete each medicine schedule");
      return;
    }

    if (
      (caregiver.name.trim() && !caregiver.phone.trim()) ||
      (!caregiver.name.trim() && caregiver.phone.trim())
    ) {
      showToast("Complete caregiver details");
      return;
    }

    const dataToSubmit = {
      name: patient.name.trim(),
      phone: patient.phone.trim(),
      medications: medicines.map((medicine) => ({
        name: medicine.name.trim(),
        dosage: medicine.dosage.trim(),
        times:
          medicine.frequency === "As needed"
            ? []
            : [
                medicine.time.trim(),
                ...(medicine.frequency === "Twice daily"
                  ? [medicine.secondTime.trim()]
                  : []),
              ],
        frequency: medicine.frequency,
        days: medicine.frequency === "Weekly" ? [medicine.weeklyDay] : [],
      })),
      caregivers:
        caregiver.name.trim() && caregiver.phone.trim()
          ? [
              {
                name: caregiver.name.trim(),
                phone: caregiver.phone.trim(),
                notify_when: notifyWhen,
              },
            ]
          : [],
    };

    setIsSubmitting(true);

    try {
      const response = await fetch(`${API_URL}/api/user/setup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dataToSubmit),
      });
      const result = await response.json();

      if (response.ok && result.success) {
        showToast("Reminders saved");
        setPatient({ name: "", phone: "" });
        setMedicines([emptyMedicine()]);
        setCaregiver({ name: "", phone: "" });
        setNotifyWhen(NOTIFY_OPTIONS[0]);
      } else {
        showToast(result.error || "Could not save reminders");
      }
    } catch {
      showToast("Could not reach the reminder API");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <style>{styles}</style>
      <form className="page" onSubmit={handleSubmit}>
        <div className="eyebrow">Med Remind</div>
        <h1>Set up reminders</h1>
        <p className="subtitle">
          Takes under two minutes. Everything can be edited later.
        </p>

        <section className="sec">
          <div className="sec-label">Who's taking this?</div>
          <div className="row r2">
            <Field label="Full name" htmlFor="p-name">
              <input
                id="p-name"
                type="text"
                placeholder="Jane Smith"
                autoComplete="name"
                value={patient.name}
                onChange={(event) =>
                  setPatient({ ...patient, name: event.target.value })
                }
              />
            </Field>
            <Field label="Phone number" htmlFor="p-phone">
              <input
                id="p-phone"
                type="tel"
                placeholder="+1 555 123 4567"
                autoComplete="tel"
                value={patient.phone}
                onChange={(event) =>
                  setPatient({ ...patient, phone: event.target.value })
                }
              />
            </Field>
          </div>
        </section>

        <section className="sec">
          <div className="sec-label">Medicines</div>
          <div className="med-list">
            {medicines.map((medicine, index) => (
              <div className="med-entry" key={index}>
                <div className="med-entry-head">
                  <span className="med-num">Medicine {index + 1}</span>
                  <button
                    type="button"
                    className="med-remove"
                    onClick={() => removeMedicine(index)}
                    aria-label={`Remove medicine ${index + 1}`}
                  >
                    remove
                  </button>
                </div>
                <div className="row r3">
                  <Field label="Name" htmlFor={`mname-${index}`}>
                    <input
                      id={`mname-${index}`}
                      type="text"
                      placeholder="e.g. Metformin"
                      value={medicine.name}
                      onChange={(event) =>
                        updateMedicine(index, "name", event.target.value)
                      }
                    />
                  </Field>
                  <Field label="Dosage" htmlFor={`mdose-${index}`}>
                    <input
                      id={`mdose-${index}`}
                      type="text"
                      placeholder="500 mg"
                      value={medicine.dosage}
                      onChange={(event) =>
                        updateMedicine(index, "dosage", event.target.value)
                      }
                    />
                  </Field>
                  <Field label="Remind at" htmlFor={`mtime-${index}`}>
                    <input
                      id={`mtime-${index}`}
                      type="time"
                      disabled={medicine.frequency === "As needed"}
                      value={medicine.time}
                      onChange={(event) =>
                        updateMedicine(index, "time", event.target.value)
                      }
                    />
                  </Field>
                </div>
                <div className="freq-label">Frequency</div>
                <div className="chip-row">
                  {FREQS.map((freq) => (
                    <button
                      type="button"
                      key={freq}
                      className={`chip ${
                        medicine.frequency === freq ? "active" : ""
                      }`}
                      onClick={() => updateMedicine(index, "frequency", freq)}
                    >
                      {freq}
                    </button>
                  ))}
                </div>
                {medicine.frequency === "Twice daily" && (
                  <div className="row r2 schedule-extra">
                    <Field label="Second reminder" htmlFor={`msecond-${index}`}>
                      <input
                        id={`msecond-${index}`}
                        type="time"
                        value={medicine.secondTime}
                        onChange={(event) =>
                          updateMedicine(index, "secondTime", event.target.value)
                        }
                      />
                    </Field>
                  </div>
                )}
                {medicine.frequency === "Weekly" && (
                  <>
                    <div className="freq-label">Reminder day</div>
                    <div className="chip-row">
                      {WEEKDAYS.map((day) => (
                        <button
                          type="button"
                          key={day}
                          className={`chip ${
                            medicine.weeklyDay === day ? "active" : ""
                          }`}
                          onClick={() => updateMedicine(index, "weeklyDay", day)}
                        >
                          {day}
                        </button>
                      ))}
                    </div>
                  </>
                )}
                {medicine.frequency === "As needed" && (
                  <p className="schedule-note">
                    No automatic reminders will be sent for this medicine.
                  </p>
                )}
              </div>
            ))}
          </div>

          <button
            type="button"
            className="add-row"
            onClick={addMedicine}
            aria-label="Add another medicine"
          >
            <span className="add-icon" aria-hidden="true">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path
                  d="M6 1v10M1 6h10"
                  stroke="#9B9890"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
            </span>
            <span className="add-text">Add another medicine</span>
          </button>
        </section>

        <section className="sec">
          <div className="sec-label">
            Caregiver <span>optional</span>
          </div>
          <div className="row r2">
            <Field label="Caregiver name" htmlFor="cg-name">
              <input
                id="cg-name"
                type="text"
                placeholder="Robert Smith"
                autoComplete="name"
                value={caregiver.name}
                onChange={(event) =>
                  setCaregiver({ ...caregiver, name: event.target.value })
                }
              />
            </Field>
            <Field label="Their phone" htmlFor="cg-phone">
              <input
                id="cg-phone"
                type="tel"
                placeholder="+1 555 987 6543"
                autoComplete="tel"
                value={caregiver.phone}
                onChange={(event) =>
                  setCaregiver({ ...caregiver, phone: event.target.value })
                }
              />
            </Field>
          </div>
          <div className="cg-notify-label">When to notify them</div>
          <div className="chip-row">
            {NOTIFY_OPTIONS.map((option) => (
              <button
                type="button"
                key={option}
                className={`chip ${notifyWhen === option ? "active" : ""}`}
                onClick={() => setNotifyWhen(option)}
              >
                {option}
              </button>
            ))}
          </div>
        </section>

        <div className="save-wrap">
          <button className="save-btn" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : "Save reminders"}
          </button>
          <p className="save-note">
            Reminders are sent via SMS to the phone number above.
          </p>
        </div>
      </form>

      <div className={`toast ${toastVisible ? "show" : ""}`}>{toast}</div>
    </>
  );
}

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div className="field">
      <label htmlFor={htmlFor}>{label}</label>
      {children}
    </div>
  );
}

const styles = `
*, *::before, *::after { box-sizing: border-box; }

:root {
  --bg:       #F8F7F4;
  --surface:  #FFFFFF;
  --border:   #E5E3DE;
  --border2:  #D0CEC8;
  --text:     #18180F;
  --muted:    #9B9890;
  --hint:     #C2C0BA;
  --accent:   #18180F;
  --chip-sel-bg: #18180F;
  --chip-sel-fg: #FFFFFF;
  --danger:   #C94040;
  --r-md:     8px;
  --r-lg:     12px;
  --max:      580px;
}

body {
  font-family: 'Outfit', sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  padding: 0 16px 100px;
}

button,
input {
  font: inherit;
}

.page {
  max-width: var(--max);
  margin: 0 auto;
  padding-top: clamp(32px, 6vw, 56px);
}

.eyebrow {
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 10px;
}

h1 {
  font-size: clamp(26px, 5vw, 34px);
  font-weight: 500;
  line-height: 1.15;
  letter-spacing: -0.3px;
  margin-bottom: 8px;
}

.subtitle {
  font-size: 14px;
  font-weight: 300;
  color: var(--muted);
  margin-bottom: 44px;
}

.sec { margin-bottom: 40px; }

.sec-label {
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
  padding-bottom: 12px;
  border-bottom: 0.5px solid var(--border);
  margin-bottom: 18px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.sec-label span {
  font-size: 10px;
  font-weight: 400;
  letter-spacing: 0.03em;
  text-transform: none;
  color: var(--hint);
}

.row {
  display: grid;
  gap: 14px;
  margin-bottom: 14px;
}

.r2 { grid-template-columns: 1fr 1fr; }
.r3 { grid-template-columns: 2fr 1fr 1.1fr; }

@media (max-width: 480px) {
  .r2 { grid-template-columns: 1fr; }
  .r3 { grid-template-columns: 1fr; }
}

.field label {
  display: block;
  font-size: 11px;
  font-weight: 400;
  color: var(--muted);
  margin-bottom: 6px;
  letter-spacing: 0.02em;
}

.field input {
  width: 100%;
  padding: 10px 13px;
  background: var(--surface);
  border: 0.5px solid var(--border);
  border-radius: var(--r-md);
  font-family: 'Outfit', sans-serif;
  font-size: 14px;
  font-weight: 400;
  color: var(--text);
  outline: none;
  transition: border-color 0.15s;
  -webkit-appearance: none;
}

.field input::placeholder { color: var(--hint); }
.field input:focus { border-color: var(--border2); }
.field input:disabled {
  color: var(--hint);
  background: #FBFAF8;
  cursor: not-allowed;
}
input[type="time"] { cursor: pointer; }

.med-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.med-entry {
  background: var(--surface);
  border: 0.5px solid var(--border);
  border-radius: var(--r-lg);
  padding: 16px 18px;
  position: relative;
  transition: border-color 0.15s, opacity 0.2s;
}

.med-entry:focus-within { border-color: var(--border2); }

.med-entry-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.med-num {
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--hint);
}

.med-remove {
  font-size: 12px;
  font-weight: 400;
  color: var(--hint);
  background: none;
  border: none;
  cursor: pointer;
  font-family: 'Outfit', sans-serif;
  padding: 2px 0;
  transition: color 0.15s;
  line-height: 1;
}

.med-remove:hover { color: var(--danger); }

.freq-label {
  font-size: 11px;
  color: var(--muted);
  margin-bottom: 8px;
  margin-top: 14px;
}

.schedule-extra {
  margin-top: 14px;
  margin-bottom: 0;
}

.schedule-note {
  font-size: 12px;
  color: var(--hint);
  margin-top: 10px;
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.chip {
  font-family: 'Outfit', sans-serif;
  font-size: 12px;
  font-weight: 400;
  padding: 6px 13px;
  border-radius: 100px;
  border: 0.5px solid var(--border2);
  color: var(--muted);
  background: none;
  cursor: pointer;
  transition: all 0.12s;
  white-space: nowrap;
  line-height: 1;
}

.chip:hover {
  border-color: var(--text);
  color: var(--text);
}

.chip.active {
  background: var(--chip-sel-bg);
  color: var(--chip-sel-fg);
  border-color: var(--chip-sel-bg);
}

.add-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0 2px;
  cursor: pointer;
  width: fit-content;
  border: 0;
  background: transparent;
  font-family: 'Outfit', sans-serif;
}

.add-row:hover .add-icon { background: var(--border2); }
.add-row:hover .add-text { color: var(--text); }

.add-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s;
}

.add-icon svg { display: block; }

.add-text {
  font-size: 13px;
  font-weight: 400;
  color: var(--muted);
  transition: color 0.15s;
}

.cg-notify-label {
  font-size: 11px;
  color: var(--muted);
  margin-bottom: 8px;
  margin-top: 16px;
}

.save-wrap { margin-top: 8px; }

.save-btn {
  width: 100%;
  padding: 14px;
  background: var(--text);
  color: #fff;
  border: none;
  border-radius: var(--r-lg);
  font-family: 'Outfit', sans-serif;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  letter-spacing: 0.01em;
  transition: opacity 0.15s, transform 0.1s;
}

.save-btn:hover { opacity: 0.88; }
.save-btn:active { transform: scale(0.995); }
.save-btn:disabled { cursor: not-allowed; opacity: 0.55; }

.save-note {
  font-size: 12px;
  color: var(--hint);
  text-align: center;
  margin-top: 10px;
}

.toast {
  position: fixed;
  bottom: 28px;
  left: 50%;
  transform: translateX(-50%) translateY(20px);
  background: var(--text);
  color: #fff;
  font-family: 'Outfit', sans-serif;
  font-size: 13px;
  font-weight: 400;
  padding: 11px 22px;
  border-radius: 100px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.25s, transform 0.25s;
  white-space: nowrap;
  z-index: 999;
}

.toast.show {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}
`;
