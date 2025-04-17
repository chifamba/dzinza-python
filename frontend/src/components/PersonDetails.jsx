import React from 'react';

const PersonDetails = ({ selectedPerson }) => {
  if (!selectedPerson) {
    return <div>Select a person to show the details</div>;
  }

  return (
    <div>
      <h3>{selectedPerson.name}</h3>
    </div>
  );
};

export default PersonDetails;