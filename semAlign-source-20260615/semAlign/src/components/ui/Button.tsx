import React from 'react';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: React.ReactNode;
}

const variantStyles: Record<string, React.CSSProperties> = {
  primary: { backgroundColor: '#2563eb', color: '#ffffff' },
  secondary: { backgroundColor: '#f1f5f9', color: '#334155' },
  ghost: { backgroundColor: 'transparent', color: '#475569' },
  danger: { backgroundColor: '#dc2626', color: '#ffffff' },
};

const variantHoverStyles: Record<string, React.CSSProperties> = {
  primary: { backgroundColor: '#1d4ed8' },
  secondary: { backgroundColor: '#e2e8f0' },
  ghost: { backgroundColor: '#f1f5f9' },
  danger: { backgroundColor: '#b91c1c' },
};

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  disabled,
  className = '',
  style,
  ...props
}) => {
  const [isHovered, setIsHovered] = React.useState(false);

  const sizeStyles: React.CSSProperties = {
    sm: { padding: '6px 12px', fontSize: '14px' },
    md: { padding: '8px 16px', fontSize: '16px' },
    lg: { padding: '12px 24px', fontSize: '18px' },
  };

  const baseStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: 500,
    borderRadius: '6px',
    transition: 'all 0.2s',
    border: 'none',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
    ...variantStyles[variant],
    ...(isHovered && !disabled ? variantHoverStyles[variant] : {}),
    ...sizeStyles[size],
    ...style,
  };

  return (
    <button
      className={className}
      style={baseStyle}
      disabled={disabled || loading}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      {...props}
    >
      {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
      {!loading && icon && <span className="mr-2">{icon}</span>}
      {children}
    </button>
  );
};

export default Button;