import type {
  InputHTMLAttributes,
  LabelHTMLAttributes,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";
import { cn } from "@/lib/utils";

export const fieldClass =
  "mt-1 w-full rounded-[3px] border border-[var(--line)] bg-[var(--bg-raised)] px-3 text-[13px] text-[var(--ink)] outline-none transition placeholder:text-[var(--ink-3)] focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)]";

export function FieldLabel({
  className,
  ...props
}: LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={cn("block text-xs font-medium text-[var(--muted)]", className)}
      {...props}
    />
  );
}

export function Input({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(fieldClass, "h-8", className)} {...props} />;
}

export function Select({
  className,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn(fieldClass, "h-8", className)} {...props} />;
}

export function Textarea({
  className,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(fieldClass, "min-h-20 resize-y py-2 leading-6", className)}
      {...props}
    />
  );
}
