import React, { useState, useEffect, useRef } from 'react';
import './Chat.css';

function Chat({ refNumber, documentSummary, onComplete }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState({ filled: 0, total: 0 });
  const [currentPlaceholder, setCurrentPlaceholder] = useState(null);
  const [showAutoSuggest, setShowAutoSuggest] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Initial load - get first question
    loadNextQuestion();
  }, []);

  const loadNextQuestion = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/placeholders/${refNumber}`);
      const data = await response.json();
      
      setProgress({
        filled: data.progress.filled + data.progress.auto_filled,
        total: data.progress.total
      });

      // Find first pending placeholder
      const pending = data.placeholders.find(p => p.status === 'pending');
      
      if (pending) {
        // Check if this question is already the last message (avoid duplicates)
        setCurrentPlaceholder(prevPlaceholder => {
          // Only add message if it's a different placeholder
          if (!prevPlaceholder || prevPlaceholder.placeholder_id !== pending.placeholder_id) {
            const questionText = pending.prompt_text || `Please provide ${pending.placeholder_name}`;
            setMessages(prev => {
              // Double-check the last message isn't already this question
              const lastMsg = prev[prev.length - 1];
              if (lastMsg && lastMsg.type === 'bot' && lastMsg.text === questionText) {
                return prev; // Skip duplicate
              }
              return [...prev, {
                type: 'bot',
                text: questionText,
                placeholder: pending
              }];
            });
          }
          return pending;
        });
      } else {
        // All done! Generate final document
        await generateFinalDoc();
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        type: 'error',
        text: 'Error loading questions: ' + err.message
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || !currentPlaceholder) return;

    const userMessage = input.trim();
    setInput('');
    
    // Add user message
    setMessages(prev => [...prev, { type: 'user', text: userMessage }]);
    setLoading(true);

    try {
      const response = await fetch(
        `/fill_placeholder/${refNumber}/${currentPlaceholder.placeholder_id}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_input: userMessage,
            consent_auto_suggest: showAutoSuggest
          })
        }
      );

      const data = await response.json();

      if (data.status === 'accepted') {
        setMessages(prev => [...prev, {
          type: 'bot',
          text: `✓ Got it! Saved as: ${data.normalized_value}`
        }]);
        setShowAutoSuggest(false);
        setTimeout(() => loadNextQuestion(), 1000);
        
      } else if (data.status === 'rejected') {
        setMessages(prev => [...prev, {
          type: 'bot',
          text: `❌ ${data.hint}\n\nPlease try again (Attempt ${data.attempts + 1}/2)`
        }]);
        
      } else if (data.status === 'offer_auto_suggest') {
        setMessages(prev => [...prev, {
          type: 'bot',
          text: '🤔 Having trouble? I can suggest a value based on the document context.'
        }]);
        setShowAutoSuggest(true);
        
      } else if (data.status === 'auto_filled') {
        setMessages(prev => [...prev, {
          type: 'bot',
          text: `✨ Auto-filled with: ${data.value}`
        }]);
        setShowAutoSuggest(false);
        setTimeout(() => loadNextQuestion(), 1000);
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        type: 'error',
        text: 'Error: ' + err.message
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSkipAutoSuggest = () => {
    setShowAutoSuggest(false);
    setMessages(prev => [...prev, {
      type: 'bot',
      text: 'Okay, please provide the value manually.'
    }]);
  };

  const handleAcceptAutoSuggest = async () => {
    setMessages(prev => [...prev, { type: 'user', text: '(Accept auto-suggestion)' }]);
    setInput('dummy'); // Trigger with consent
    setShowAutoSuggest(true);
    
    // Submit with auto-suggest consent
    setLoading(true);
    try {
      const response = await fetch(
        `/fill_placeholder/${refNumber}/${currentPlaceholder.placeholder_id}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_input: 'auto',
            consent_auto_suggest: true
          })
        }
      );

      const data = await response.json();

      if (data.status === 'auto_filled') {
        setMessages(prev => [...prev, {
          type: 'bot',
          text: `✨ Auto-filled with: ${data.value}`
        }]);
        setShowAutoSuggest(false);
        setTimeout(() => loadNextQuestion(), 1000);
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        type: 'error',
        text: 'Error: ' + err.message
      }]);
    } finally {
      setLoading(false);
    }
  };

  const generateFinalDoc = async () => {
    setLoading(true);
    setMessages(prev => [...prev, {
      type: 'bot',
      text: '🎉 All placeholders filled! Generating final document...'
    }]);

    try {
      const response = await fetch(`/generate_final_doc/${refNumber}`, {
        method: 'POST'
      });

      const data = await response.json();

      if (data.status === 'ok') {
        onComplete(data.final_document);
      } else {
        setMessages(prev => [...prev, {
          type: 'error',
          text: 'Error generating document: ' + (data.error || 'Unknown error')
        }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        type: 'error',
        text: 'Error: ' + err.message
      }]);
    } finally {
      setLoading(false);
    }
  };

  const progressPercent = progress.total > 0 
    ? (progress.filled / progress.total) * 100 
    : 0;

  return (
    <>
      <div className="header">
        <h1>💬 Filling Placeholders</h1>
        <div className="reference-badge">Reference #{refNumber}</div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progressPercent}%` }} />
        </div>
        <p style={{ marginTop: '12px', fontSize: '14px' }}>
          {progress.filled} of {progress.total} complete
        </p>
      </div>

      <div className="chat-container">
        <div className="chat-messages">
          <div className="message bot">
            <div className="message-content">
              📋 <strong>Document Summary:</strong><br/>
              {documentSummary}
            </div>
          </div>

          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.type}`}>
              <div className="message-content">
                {msg.text.split('\n').map((line, i) => (
                  <React.Fragment key={i}>
                    {line}
                    {i < msg.text.split('\n').length - 1 && <br />}
                  </React.Fragment>
                ))}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message bot">
              <div className="message-content typing">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-container">
          {showAutoSuggest && (
            <div className="auto-suggest-buttons">
              <button onClick={handleAcceptAutoSuggest} className="accept-btn">
                ✨ Accept Auto-Suggestion
              </button>
              <button onClick={handleSkipAutoSuggest} className="skip-btn">
                ✏️ Fill Manually
              </button>
            </div>
          )}

          <form onSubmit={handleSubmit} className="chat-input-form">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your answer..."
              disabled={loading || showAutoSuggest}
              className="chat-input"
            />
            <button 
              type="submit" 
              disabled={loading || !input.trim() || showAutoSuggest}
              className="send-btn"
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </>
  );
}

export default Chat;

