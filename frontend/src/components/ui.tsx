import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";

export function StatusBadge({ status, testId }: { status: string; testId?: string }) {
  return (
    <span className={`badge badge-${status.toLowerCase()}`} data-testid={testId}>
      {status}
    </span>
  );
}

export function ErrorAlert({ message }: { message: string | null }) {
  return message ? <p role="alert" className="alert">{message}</p> : null;
}

export function Notice({ message }: { message: string | null }) {
  return message ? <p role="status" className="notice">{message}</p> : null;
}

export function Panel({ title, children, className }: { title: string; children: ReactNode; className?: string }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className={`panel ${className ?? ""}`}>
      <h2 id={id}>{title}</h2>
      {children}
    </section>
  );
}

type FieldProps = InputHTMLAttributes<HTMLInputElement> & { label: string };

export function Field({ label, ...input }: FieldProps) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input id={id} {...input} />
    </div>
  );
}

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & { label: string; options: string[] };

export function SelectField({ label, options, ...select }: SelectProps) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select id={id} {...select}>
        {options.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    </div>
  );
}

export function Money({ value }: { value: string | null | undefined }) {
  return <span className="money">{value ?? "—"}</span>;
}
