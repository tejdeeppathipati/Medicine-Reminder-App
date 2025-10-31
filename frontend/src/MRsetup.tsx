import React, { useState } from "react";

// MRsetup.tsx
// react for the medicine reminder setup form takes care of user input, medicine, caregiverd, form submission, and alerts
// sets connection to the api to save user data when form is submitted
// logic includes adding and removing medicines or caregivers and displaying success/error messages when the form is submitted.
// tailwind css gives a cleaner look for the users

interface Medicine {
  name: string;
  dosage: string;
  time: string;
}

interface Caregiver {
  name: string;
  phone: string;
}

interface Alert { // needed interface to tell if the form submissions are working or not.
  type: "success" | "error";
  message: string;
}

export default function MedicineSetup() {
  const [medicines, setMedicines] = useState<Medicine[]>([ // list for medicines
    { name: "", dosage: "", time: "" },
  ]);
  const [caregivers, setCaregivers] = useState<Caregiver[]>([ // list for caregivers
    { name: "", phone: "" },
  ]);
  const [userInfo, setUserInfo] = useState({ name: "", phone: "" });
  const [alert, setAlert] = useState<Alert | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false); //

  const handleMedicineChange = ( // function to update one medicine
    index: number,
    field: keyof Medicine,
    value: string
  ) => {
    const newMeds = [...medicines];
    newMeds[index][field] = value;
    setMedicines(newMeds);
  };

  const handleCaregiverChange = ( // function to update one caregiver
    index: number,
    field: keyof Caregiver,
    value: string
  ) => {
    const newCaregivers = [...caregivers];
    newCaregivers[index][field] = value;
    setCaregivers(newCaregivers);
  };

  const addMedicine = () => { // function for new empty medicine
    setMedicines([...medicines, { name: "", dosage: "", time: "" }]);
  };

  const removeMedicine = (index: number) => { // function to remove one medicine. should not allow no medicines to show
    if (medicines.length > 1) {
      setMedicines(medicines.filter((_, i) => i !== index));
    }
  };

  const addCaregiver = () => { // function for new empty caregiver
    setCaregivers([...caregivers, { name: "", phone: "" }]);
  };

  const removeCaregiver = (index: number) => { // function for to remove one caergiver, should allow removal of all
    setCaregivers(caregivers.filter((_, i) => i !== index));
  };

  // all submission handling below. form functionality relies on this most importantly
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);

    if (!userInfo.name || !userInfo.phone) {
      setAlert({ type: "error", message: "Please fill out all user fields." });
      setIsSubmitting(false);
      return;
    }

    if (medicines.some((m) => !m.name || !m.dosage || !m.time)) {
      setAlert({ type: "error", message: "Please add at least one medicine." });
      setIsSubmitting(false);
      return;
    }

    const validCaregivers = caregivers.filter(
      (cg) => cg.name.trim() && cg.phone.trim()
    );

// actual data being extracted from the form this is what preps json for the api
    const dataToSubmit = {
      name: userInfo.name.trim(),
      phone: userInfo.phone.trim(),
      medications: medicines.map((med) => ({
        name: med.name.trim(),
        dosage: med.dosage.trim(),
        time: med.time.trim(),
      })),
      caregivers: validCaregivers,
    };

    
    try {

      // this should send data to the backend api which then writes to mongodb
      const response = await fetch("http://127.0.0.1:5000/api/user/setup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dataToSubmit), // data should be json string
      });

    
      const result = await response.json();

      if (response.ok) {
        setAlert({ type: "success", message: "Setup complete! You will now receive SMS reminders." });
        setTimeout(() => {
          setUserInfo({ name: "", phone: "" });
          setMedicines([{ name: "", dosage: "", time: "" }]);
          setCaregivers([{ name: "", phone: "" }]);
          setAlert(null);
        }, 5000);

      } else { // error messages, two types depending on failed submissions
        setAlert({ type: "error", message: result.error || "Setup failed. Try again." });
      }
    } catch (error) {
      setAlert({ type: "error", message: "Error. Check your connection." });
    } finally {
      setIsSubmitting(false);
    }
  };


  // appearance changes (JSX)
  return (
    // big page container with light grey background and same padding for cleaner look, simple for target audience
    <div className = "min-h-screen bg-gray-100 py-8 px-4">
      
      {/* main content. using a rounded box elevates the page and looks cleaner, white contrasts the background */}
      <div className = "max-w-2xl mx-auto bg-white rounded-lg shadow p-6">
        
        {/* title text should be bigger and more prominent than the rest of the form */}
        <h1 className = "text-3xl font-bold text-gray-900 mb-2">
          Medicine Reminder Setup
        </h1>
        {/* description for rhe form, simple and to the point for the user */}
        <p className = "text-gray-600 mb-6">
          Set up your medicine reminders and add optional caregivers
        </p>

        {/* alerts show up at the top of the form if set up was successful or not */}
        {alert && (
          <div
            className = {`p-3 mb-4 rounded ${
              // if/else for background color (red for failure and green for success)
              alert.type === "success" ? "bg-green-300 text-green-800" : "bg-red-300 text-red-900" 
            }`}
          >
            {alert.message}
          </div>
        )}

        {/* form container inside the background. this part handles user entered submissions (ensure space between section for better appearance */}
        <form onSubmit = {handleSubmit} className = "space-y-6">
          <div>
            {/* all user info go here. this is a heading and should be bolder than the text below. */}
            <h2 className = "text-lg font-semibold text-gray-900 mb-3">
              Your Information
            </h2>
            <div className = "space-y-3">
              {/* box for user to input name */}
              <input
                value = {userInfo.name}
                onChange={(e) => setUserInfo({ ...userInfo, name: e.target.value })} // updates user name when changed
                placeholder = "Your Name"
                className = "w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
              {/* box for phone number input */}
              <input
                value = {userInfo.phone}
                onChange = {(e) => setUserInfo({ ...userInfo, phone: e.target.value })} // updates phone number when changed
                placeholder = "Phone Number" // tells user what to put here. appears until information is typed
                className = "w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500"
                // purple rings appears on all text boxes when they are clicked and being typed in
              />
            </div>
          </div>

          <div>
            {/* medicine section, another heading and should be bolder than the rest of the text. holds the medicine, dosage, and time */}
            <h2 className = "text-lg font-semibold text-gray-900 mb-3">
              Medicines
            </h2>
            <div className = "space-y-3">
              {/* medicine array, loop through and create an item for each added */}
              {medicines.map((med, index) => (
                <div key = {index} className = "p-3 border border-gray-300 rounded bg-gray-50"> 
                {/* this and the caregivers sections rounded box within the form with slight color difference for added contrast, looks better for the user */}
                  <div className = "flex justify-between items-center mb-2">
                    <span className = "text-sm font-medium text-gray-700">
                      Medicine {index + 1}
                    </span>
                    {/* the remove button only appears if more than one medicine is entered, this should appear on all medicines
                    a user should not be allowed to remove medicine if it is the only one logged */}
                    {medicines.length > 1 && (
                      <button
                        type = "button"
                        onClick = {() => removeMedicine(index)}
                        className = "text-black-600 text-sm hover:text-black-800 underline"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                  <div className = "space-y-2">
                    {/* medicine name input button */}
                    <input
                      value = {med.name}
                      onChange = {(e) => handleMedicineChange(index, "name", e.target.value)}
                      placeholder = "Medicine Name"
                      className = "w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                    {/* medicine dosage input */}
                    <input
                       value = {med.dosage}
                       onChange = {(e) => handleMedicineChange(index, "dosage", e.target.value)}
                       placeholder = "Dosage"
                       className = "w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                    {/* input space for the time reminder should be sent */}
                    <input
                      value = {med.time}
                      onChange = {(e) => handleMedicineChange(index, "time", e.target.value)}
                      placeholder = "Time (ex: 8:00 AM, 2:30 PM)"
                      className = "w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                </div>
              ))}
              {/* this button should allow a user to add more medicine to receive more reminders. */}
              <button
                type = "button"
                onClick = {addMedicine}
                className = "w-full py-2 px-4 border border-gray-300 text-gray-700 rounded hover:bg-gray-50"
              >
                Add More Medicine
              </button>
            </div>
          </div>

          <div>
            {/* caregivers section: the heading should be bold and clear that this section is optional, description should be below it for clarity */}
            <h2 className = "text-lg font-semibold text-gray-900 mb-3">
              Caregivers (Optional)
            </h2>
            <p className = "text-sm text-gray-600 mb-3">
              Your caregivers will be notified if you miss several reminders
            </p>
            <div className = "space-y-3">
              {/* caregivers array: loop through if a user decides to add a caregiver */}
              {caregivers.map((caregiver, index) => (
                <div key = {index} className = "p-3 border border-gray-300 rounded bg-gray-50">
                  <div className = "flex justify-between items-center mb-2">
                    <span className = "text-sm font-medium text-gray-700">
                      Caregiver {index + 1}
                    </span>
                    {/* remove caregiver button, similar to remove medicine except a user can remove all caregivers if none needed */}
                    <button
                      type="button"
                      onClick={() => removeCaregiver(index)}
                      className = "text-black-600 text-sm underline hover:text-black-800"
                    >
                      Remove
                    </button>
                  </div>
                  <div className = "space-y-2">
                    {/* caregiver name input, placeholder tells user what to put here */}
                    <input
                      value = {caregiver.name}
                      onChange = {(e) => handleCaregiverChange(index, "name", e.target.value)}
                      placeholder = "Caregiver Name"
                      className = "w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                    {/* caregive phone number goes here */}
                    <input
                      value = {caregiver.phone}
                      onChange = {(e) => handleCaregiverChange(index, "phone", e.target.value)}
                      placeholder = "Caregiver Phone Number"
                      className = "w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500"
                    /> 
                  </div>
                </div>
              ))}
              {/* button to add caregiver */}
              <button
                type = "button"
                onClick = {addCaregiver}
                className = "w-full py-2 px-4 border border-gray-300 text-gray-700 rounded hover:bg-gray-50"
              >
                Add Caregiver
              </button>
            </div>
          </div>

          {/* submit button, different color than all buttons on the form (important for clarity and distinction) */}
          <button
            type = "submit"
            disabled = {isSubmitting} // button should be disabled when form is submitting to prevent issues
            className = "w-full py-3 px-6 bg-purple-800 text-white rounded font-semibold hover:bg-purple-900 disabled:bg-gray-400"
          >
            {/* conditional text for the save button */}
            {isSubmitting ? "Working.. please wait." : "Save"}
          </button>
        </form>
      </div>
    </div>
)};
