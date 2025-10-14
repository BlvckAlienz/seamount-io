// File Location: frontend/src/components/QRCodeGenerator.tsx
import React, { useEffect, useRef } from 'react';
import QRCodeStyling from 'qr-code-styling';

interface QRCodeGeneratorProps {
  data: string;
  size?: number;
}

const QRCodeGenerator: React.FC<QRCodeGeneratorProps> = ({ data, size = 256 }) => {
  const ref = useRef<HTMLDivElement>(null);
  const qrCode = useRef<QRCodeStyling | null>(null);

  useEffect(() => {
    if (!qrCode.current) {
      qrCode.current = new QRCodeStyling({
        width: size,
        height: size,
        data: data,
        margin: 10,
        qrOptions: { typeNumber: 0, mode: 'Byte', errorCorrectionLevel: 'Q' },
        imageOptions: { hideBackgroundDots: true, imageSize: 0.4, margin: 0 },
        dotsOptions: {
          type: 'rounded',
          color: '#1f2937',
          gradient: {
            type: 'linear',
            rotation: 0,
            colorStops: [
              { offset: 0, color: '#3b82f6' },
              { offset: 1, color: '#8b5cf6' }
            ]
          }
        },
        backgroundOptions: { color: '#ffffff' },
        cornersSquareOptions: { type: 'extra-rounded', color: '#1f2937' },
        cornersDotOptions: { type: 'dot', color: '#3b82f6' }
      });
    }

    if (ref.current) {
      ref.current.innerHTML = '';
      qrCode.current.append(ref.current);
    }
  }, [data, size]);

  useEffect(() => {
    if (qrCode.current) {
      qrCode.current.update({ data });
    }
  }, [data]);

  return <div ref={ref} className="flex items-center justify-center" />;
};

export default QRCodeGenerator;