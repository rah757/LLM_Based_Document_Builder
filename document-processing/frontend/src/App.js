import React, { useState } from 'react';
import './App.css';
import Upload from './components/Upload';
import Chat from './components/Chat';
import Complete from './components/Complete';

function App() {
  const [step, setStep] = useState('upload'); // upload, chat, complete
  const [refNumber, setRefNumber] = useState(null);
  const [documentSummary, setDocumentSummary] = useState('');
  const [finalDocument, setFinalDocument] = useState('');

  const handleUploadSuccess = (data) => {
    setRefNumber(data.reference_number);
    setDocumentSummary(data.document_summary);
    setStep('chat');
  };

  const handleChatComplete = (finalDoc) => {
    setFinalDocument(finalDoc);
    setStep('complete');
  };

  const handleStartOver = () => {
    setStep('upload');
    setRefNumber(null);
    setDocumentSummary('');
    setFinalDocument('');
  };

  return (
    <div className="App">
      {step === 'upload' && (
        <Upload onSuccess={handleUploadSuccess} />
      )}
      
      {step === 'chat' && (
        <Chat 
          refNumber={refNumber} 
          documentSummary={documentSummary}
          onComplete={handleChatComplete}
        />
      )}
      
      {step === 'complete' && (
        <Complete 
          refNumber={refNumber}
          finalDocument={finalDocument}
          onStartOver={handleStartOver}
        />
      )}
    </div>
  );
}

export default App;

