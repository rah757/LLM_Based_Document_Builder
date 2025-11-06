import React from 'react';
import './Complete.css';

function Complete({ refNumber, finalDocument, onStartOver }) {
  const downloadUrl = `http://localhost:5051/download/${refNumber}/${finalDocument}`;
  const isDraft = finalDocument.includes('draft');

  const handleDownload = () => {
    // Use window.open to trigger download
    window.open(downloadUrl, '_blank');
  };

  return (
    <>
      <div className="header">
        <h1>🎉 Document Complete!</h1>
        <div className="reference-badge">Reference #{refNumber}</div>
      </div>

      <div className="container complete-container">
        <div className="success-icon">✓</div>
        
        <h2>Your document is ready!</h2>
        
        {isDraft && (
          <div className="draft-notice">
            ⚠️ This is a <strong>draft</strong> document (contains auto-filled values)
          </div>
        )}
        
        <p className="complete-text">
          All placeholders have been filled and your final document has been generated.
        </p>

        <div className="complete-actions">
          <button onClick={handleDownload} className="download-btn">
            📥 Download {finalDocument}
          </button>

          <button onClick={onStartOver} className="secondary">
            🔄 Process Another Document
          </button>
        </div>

        <div className="info-box">
          <h3>What's next?</h3>
          <ul>
            <li>Review the document for accuracy</li>
            {isDraft && <li>Verify auto-filled values</li>}
            <li>Share with relevant parties</li>
            <li>Sign and execute as needed</li>
          </ul>
        </div>
      </div>
    </>
  );
}

export default Complete;

