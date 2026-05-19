import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { Loader2 } from 'lucide-react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-full text-xs font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]',
  {
    variants: {
      variant: {
        default:
          'border border-border bg-gradient-to-b from-secondary to-secondary/70 text-foreground shadow-[0_6px_18px_hsl(0_0%_0%/0.18)] hover:border-primary/60 hover:from-secondary hover:to-accent',
        primary:
          'bg-primary text-primary-foreground shadow-[0_6px_22px_hsl(213_94%_50%/0.35)] hover:bg-primary/90',
        outline:
          'border border-border bg-card/40 text-foreground hover:bg-accent hover:border-primary/60',
        ghost:
          'text-muted-foreground hover:bg-accent hover:text-foreground',
        danger:
          'border border-destructive/40 bg-destructive/10 text-destructive hover:bg-destructive/20 hover:border-destructive/60',
        success:
          'border border-success/40 bg-success/10 text-success hover:bg-success/20 hover:border-success/60',
      },
      size: {
        default: 'h-9 px-3.5',
        sm: 'h-7 px-2.5 text-[11px]',
        lg: 'h-10 px-5 text-sm',
        icon: 'h-9 w-9 p-0',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, loading = false, disabled, children, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    const isDisabled = disabled || loading;
    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size, className }), loading && 'cursor-wait')}
        disabled={isDisabled}
        aria-busy={loading || undefined}
        {...props}
      >
        <span className="inline-flex items-center gap-1.5">
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0" aria-hidden="true" /> : null}
          {children}
        </span>
      </Comp>
    );
  },
);
Button.displayName = 'Button';

export { Button, buttonVariants };
