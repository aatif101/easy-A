import { useEffect, useState, type FormEvent, type ReactNode } from "react";

interface SearchBoxProps {
  initialValue?: string;
  onSearch: (value: string) => void;
  size?: "large" | "compact";
  /** Optional button to render inside the search field, after the input */
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
        className={search-field flex min-w-0 flex-1 items-center gap-2.5 rounded-lg border-[1.5px] border-ink bg-white px-3.5 }
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#466069" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3.5-3.5" />
        </svg>
        <span className="sr-only">Search classes by CRN, course, or subject</span>
        <input
          type="search"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Course or CRN"
          autoComplete="off"
          spellCheck={false}
          className={min-w-0 flex-1 border-0 bg-transparent text-ink placeholder:text-slate }
        />
        {rightButton && (
          <div className="flex items-center ms-2">{rightButton}</div>
        )}
      </label>
      <button
        type="submit"
        className={shrink-0 rounded-lg bg-green px-5 font-semibold text-white hover:bg-green-deep }
      >
        Search
      </button>
    </form>
  );
}
