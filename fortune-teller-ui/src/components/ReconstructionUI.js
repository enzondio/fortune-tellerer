import React, { useState } from 'react';

const API_URL = 'http://localhost:5000';

const ReconstructionUI = () => {
  const [selectedFiles, setSelectedFiles] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [reconstructedImage, setReconstructedImage] = useState(null);

  // Define the required composites
  const composites = {
    'combo_opt_1_6': 'Options 1 & 6 pair',
    'combo_opt_2_5': 'Options 2 & 5 pair',
    'combo_opt_3_8': 'Options 3 & 8 pair',
    'combo_opt_4_7': 'Options 4 & 7 pair',
    'combo_flaps': 'All corner flaps',
    'combo_diamond': 'Center diamond'
  };

  const handleFileSelect = (event, compositeId) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFiles(prev => ({
        ...prev,
        [compositeId]: file
      }));
    }
  };

// ... other imports and code remain the same ...

  const reconstructImage = async () => {
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      Object.entries(selectedFiles).forEach(([compositeId, file]) => {
        formData.append('files', file, `${compositeId}.png`);
      });

      // Use the new endpoint
      const response = await fetch(`${API_URL}/api/reconstruct_from_composites`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to reconstruct image');
      }

      const data = await response.json();
      setReconstructedImage(data.image);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

// ... rest of the component remains the same ...

  return (
    <div className="max-w-4xl mx-auto p-4">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Upload Composite Images</h2>
        <p className="text-gray-600 mb-6">
          Upload the composite images from your fortune teller to reconstruct the complete image.
        </p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {Object.entries(composites).map(([compositeId, description]) => (
            <div key={compositeId} className="border rounded-lg p-4">
              <div className="mb-2 font-medium">{description}</div>
              <div className="flex flex-col items-center justify-center border-2 border-dashed border-gray-300 rounded-lg p-4 hover:border-gray-400 cursor-pointer">
                {selectedFiles[compositeId] ? (
                  <div className="w-full aspect-square relative">
                    <img 
                      src={URL.createObjectURL(selectedFiles[compositeId])} 
                      alt={description}
                      className="w-full h-full object-contain"
                    />
                  </div>
                ) : (
                  <div className="text-center">
                    <div className="text-gray-500 mb-2">Click to upload</div>
                  </div>
                )}
                <input 
                  type="file"
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  onChange={(e) => handleFileSelect(e, compositeId)}
                  accept="image/*"
                />
              </div>
            </div>
          ))}
        </div>

        <button
          onClick={reconstructImage}
          disabled={Object.keys(selectedFiles).length < Object.keys(composites).length || loading}
          className="w-full bg-blue-500 text-white rounded-lg px-4 py-2 font-medium hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          {loading ? 'Reconstructing...' : 'Reconstruct Image'}
        </button>

        {error && (
          <div className="mt-4 p-4 bg-red-50 text-red-600 rounded-lg">
            {error}
          </div>
        )}

        {reconstructedImage && (
          <div className="mt-6">
            <h3 className="text-lg font-semibold mb-2">Reconstructed Image</h3>
            <div className="border rounded-lg p-4">
              <img 
                src={reconstructedImage} 
                alt="Reconstructed Fortune Teller" 
                className="max-w-full mx-auto"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReconstructionUI;