import { useEffect, useState, type FormEvent, type ReactNode } from "react";

interface SearchBoxProps {
  initialValue?: string;
  onSearch: (value: string) => void;
  size?: "large" | "compact";
  /** Optional control beside the search field, before the submit button. */
  rightButton?: ReactNode;
}

export function SearchBox({ initialValue = "", onSearch, size = "large", rightButton }: SearchBoxProps) {
  const [value, setValue] = useState(initialValue);
  useEffect(() => setValue(initialValue), [initialValue]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (value.trim()) onSearch(value.trim());
  };

  const large = size === "large";
  return (
    <form role="search" onSubmit={submit} className="flex w-full items-center gap-2">
      <label
        className={`search-field flex min-w-0 flex-1 items-center gap-2.5 rounded-lg border-[1.5px] border-ink bg-white px-3.5 ${large ? "h-[52px]" : "h-11"}`}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#466069" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3.5-3.5" />
        </svg>
        <span className="sr-only">Search classes by CRN, course, subject, number, title, or professor</span>
        <input
          type="search"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Course, CRN, or professor"
          autoComplete="off"
          spellCheck={false}
          className={`min-w-0 flex-1 border-0 bg-transparent text-ink placeholder:text-slate ${large ? "text-[17px]" : "text-base"}`}
        />
      </label>
      {rightButton}
      <button
        type="submit"
        className={`shrink-0 rounded-lg bg-green px-5 font-semibold text-white hover:bg-green-deep ${large ? "h-[52px]" : "h-11"}`}
      >
        Search
      </button>
    </form>
  );
}
