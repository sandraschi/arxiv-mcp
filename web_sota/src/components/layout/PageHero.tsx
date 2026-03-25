import { useId, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export type PageHeroProps = {
  /** Small label above the title (e.g. page family name). */
  eyebrow?: string;
  title: string;
  size?: "default" | "large";
  /** One short paragraph in muted text — use for simple pages. */
  lead?: string;
  /** Extra blocks: bullet lists, buttons, links. Shown after `lead`. */
  children?: ReactNode;
  className?: string;
};

/**
 * Consistent top-of-page intro: plain language, same visual weight as the home hero.
 */
export function PageHero({ eyebrow, title, size = "default", lead, children, className }: PageHeroProps) {
  const headingId = useId();
  return (
    <section
      className={cn(
        "relative overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-primary/[0.12] via-background to-background px-6 py-6 md:px-8 md:py-8 shadow-sm",
        className,
      )}
      aria-labelledby={headingId}
    >
      <div className="relative max-w-3xl space-y-3">
        {eyebrow ? (
          <p className="text-xs font-semibold uppercase tracking-wider text-primary">{eyebrow}</p>
        ) : null}
        <h1
          id={headingId}
          className={cn(
            "font-bold tracking-tight text-foreground",
            size === "large" ? "text-3xl md:text-4xl" : "text-2xl md:text-3xl",
          )}
        >
          {title}
        </h1>
        {lead ? (
          <p className="text-muted-foreground text-sm md:text-base leading-relaxed">{lead}</p>
        ) : null}
        {children != null && children !== false ? <div className="space-y-3 pt-1">{children}</div> : null}
      </div>
    </section>
  );
}
