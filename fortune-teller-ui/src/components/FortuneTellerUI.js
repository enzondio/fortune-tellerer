import React, { useState } from 'react';

// Define API base URL - adjust port if needed
const API_URL = 'http://localhost:5000';

function FortuneTellerUI() {
  const [image, setImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [processedImages, setProcessedImages] = useState({});

  const handleImageUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => setImage(e.target.result);
      reader.readAsDataURL(file);
    }
  };

  const processImage = async () => {
    setLoading(true);
    setError(null);

    try {
      // Create FormData object to send file
      const formData = new FormData();
      
      // Convert base64 image back to file
      const response = await fetch(image);
      const blob = await response.blob();
      formData.append('file', blob, 'image.png');

      // Send to backend
      const result = await fetch(`${API_URL}/api/process`, {
        method: 'POST',
        body: formData,
      });

      if (!result.ok) {
        throw new Error('Failed to process image');
      }

      const data = await result.json();
      setProcessedImages(data.segments);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>Fortune Teller Processor</h1>
      
      <input
        type="file"
        accept="image/*"
        onChange={handleImageUpload}
        disabled={loading}
      />

      {image && (
        <button 
          onClick={processImage}
          disabled={loading}
        >
          {loading ? 'Processing...' : 'Process Image'}
        </button>
      )}

      {error && (
        <div style={{ color: 'red' }}>
          Error: {error}
        </div>
      )}

      {image && (
        <div>
          <h2>Uploaded Image:</h2>
          <img 
            src={image} 
            alt="Uploaded" 
            style={{ maxWidth: '300px' }} 
          />
        </div>
      )}

      {Object.keys(processedImages).length > 0 && (
        <div>
          <h2>Processed Segments:</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
            {Object.entries(processedImages).map(([key, src]) => (
              <div key={key}>
                <h3>{key}</h3>
                <img 
                  src={src} 
                  alt={key} 
                  style={{ maxWidth: '100%' }} 
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default FortuneTellerUI;