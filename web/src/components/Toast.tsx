import React, { useEffect } from 'react';

type Props = {
  message: string;
  actionLabel?: string;
  onAction?: () => void;
  onClose: () => void;
  timeoutMs?: number;
};

export default function Toast({ message, actionLabel, onAction, onClose, timeoutMs = 5000 }: Props) {
  useEffect(() => {
    const t = setTimeout(onClose, timeoutMs);
    return () => clearTimeout(t);
  }, [onClose, timeoutMs]);
  return (
    <div className="toast" role="status" aria-live="polite">
      <span>{message}</span>
      {actionLabel && onAction && (
        <button className="btn btn-outline" style={{ marginLeft: 8 }} onClick={onAction}>{actionLabel}</button>
      )}
      <button className="btn btn-outline" style={{ marginLeft: 8 }} onClick={onClose}>Dismiss</button>
    </div>
  );
}

