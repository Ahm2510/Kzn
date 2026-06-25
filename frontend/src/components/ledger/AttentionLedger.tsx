/**
 * AttentionLedger — the Overview hero.
 *
 * Renders the Prompt-1 `action_list` as the dominant content: a short, plain
 * "what needs you today" ledger. Each row is a leading severity seal, the
 * imperative action, and a right-aligned rupee balance that counts up on load.
 * This is the product's signature surface — risk read the way an account book
 * reads.
 */
import { Reveal, RevealItem } from "@/components/motion";
import { SeveritySeal, SignalTag, type SeverityLevel } from "@/components/ui/SeveritySeal";
import { CountUp } from "@/components/ui/CountUp";
import { formatINRLakh } from "@/lib/format";

export interface LedgerItem {
  id: string;
  level: SeverityLevel;
  tag: string;
  headline: string;
  detail?: string;
  amount?: number;
}

export function AttentionLedger({ items }: { items: LedgerItem[] }) {
  if (!items.length) return null;

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      <Reveal className="divide-y divide-border" stagger={0.07}>
        {items.map((item, i) => (
          <RevealItem key={item.id}>
            <div className="group flex items-start gap-4 px-5 py-4 transition-colors hover:bg-muted/40">
              <SeveritySeal
                level={item.level}
                size="md"
                pulse={i === 0 && item.level === "overdue"}
                className="mt-0.5"
              />
              <div className="min-w-0 flex-1">
                <SignalTag level={item.level}>{item.tag}</SignalTag>
                <p className="mt-1 text-[15px] font-medium leading-snug text-foreground">
                  {item.headline}
                </p>
                {item.detail && (
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{item.detail}</p>
                )}
              </div>
              {item.amount != null && item.amount > 0 && (
                <div className="shrink-0 pl-2 text-right">
                  <CountUp
                    value={item.amount}
                    format={formatINRLakh}
                    className="font-mono text-base font-semibold tabular-nums text-foreground"
                  />
                  <p className="mt-0.5 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                    at stake
                  </p>
                </div>
              )}
            </div>
          </RevealItem>
        ))}
      </Reveal>
    </div>
  );
}
