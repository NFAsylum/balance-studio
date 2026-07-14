"use client";
import Link from "next/link";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/lib/theme";
import { useT, type Locale } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { ModelStatusChip } from "@/components/model-status-chip";

/** App header: brand, tagline, dark-mode toggle, language switch. */
export function SiteHeader() {
  const { theme, toggle } = useTheme();
  const { t, locale, setLocale } = useT();

  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
        <div className="flex items-baseline gap-3">
          <Link href="/" className="font-semibold">
            Balance Studio
          </Link>
          <span className="hidden text-xs text-muted-foreground sm:inline">{t("tagline")}</span>
        </div>

        <div className="flex items-center gap-2">
          <ModelStatusChip />
          <LocaleSwitch locale={locale} onChange={setLocale} label={t("language")} />
          <Button
            variant="ghost"
            size="sm"
            onClick={toggle}
            aria-label={t("toggleTheme")}
            title={t("toggleTheme")}
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </header>
  );
}

function LocaleSwitch({
  locale,
  onChange,
  label,
}: {
  locale: Locale;
  onChange: (l: Locale) => void;
  label: string;
}) {
  return (
    <select
      aria-label={label}
      className="h-8 rounded-md border border-input bg-background px-2 text-xs uppercase"
      value={locale}
      onChange={(e) => onChange(e.target.value as Locale)}
    >
      <option value="en">EN</option>
      <option value="pt">PT</option>
    </select>
  );
}
