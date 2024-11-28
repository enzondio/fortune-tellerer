// src/components/ui/alert.jsx
import React from 'react';

const Alert = ({ variant = 'default', className = '', ...props }) => {
  const baseStyle = "relative w-full rounded-lg border p-4";
  const variantStyles = {
    default: "bg-white border-gray-200",
    destructive: "bg-red-50 border-red-200 text-red-700",
  };

  return (
    <div
      role="alert"
      className={`${baseStyle} ${variantStyles[variant]} ${className}`}
      {...props}
    />
  );
};

const AlertDescription = ({ className = '', ...props }) => (
  <div
    className={`text-sm text-gray-700 ${className}`}
    {...props}
  />
);

export { Alert, AlertDescription };