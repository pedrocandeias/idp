import React from 'react';

type Props = {
  open: boolean;
  title?: string;
  message?: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void;
  onCancel: () => void;
};

export default function Confirm({ open, title, message, confirmText = 'Confirm', cancelText = 'Cancel', onConfirm, onCancel }: Props) {
  if (!open) return null;
  return (
    <div role="dialog" aria-modal="true" className="modal-overlay" style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div className="panel" style={{ minWidth: 320 }}>
        {title && <h3>{title}</h3>}
        {message && <p>{message}</p>}
        <div className="row" style={{ justifyContent: 'flex-end', gap: 8 }}>
          <button onClick={onCancel}>{cancelText}</button>
          <button onClick={onConfirm}>{confirmText}</button>
        </div>
      </div>
    </div>
  );
}

