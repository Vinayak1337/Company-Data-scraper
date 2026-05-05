import type { ButtonHTMLAttributes, AnchorHTMLAttributes, ReactNode } from "react";
import Link from "next/link";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex max-w-full items-center justify-center gap-2 whitespace-nowrap rounded-[3px] border text-[13px] font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "border-[var(--line)] bg-[var(--bg-raised)] text-[var(--ink)] hover:border-[var(--line-strong)] hover:bg-[var(--bg-hover)]",
        primary:
          "border-[var(--ink)] bg-[var(--ink)] text-[var(--bg)] hover:border-[var(--ink-2)] hover:bg-[var(--ink-2)]",
        ghost:
          "border-transparent bg-transparent text-[var(--ink-2)] hover:bg-[var(--bg-hover)] hover:text-[var(--ink)]",
        danger:
          "border-[var(--line)] bg-[var(--bg-raised)] text-[var(--danger)] hover:border-[var(--danger)] hover:bg-[var(--danger-soft)]",
      },
      size: {
        sm: "h-7 px-2.5 text-xs",
        md: "h-8 px-3.5",
        lg: "h-10 px-4.5 text-sm",
        icon: "h-[30px] w-[30px] px-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  },
);

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>;

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return (
    <button
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
}

type ButtonLinkProps = AnchorHTMLAttributes<HTMLAnchorElement> &
  VariantProps<typeof buttonVariants> & {
    href: string;
    children: ReactNode;
  };

export function ButtonLink({
  className,
  variant,
  size,
  href,
  children,
  ...props
}: ButtonLinkProps) {
  return (
    <Link
      href={href}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    >
      {children}
    </Link>
  );
}
