import { Button } from "@/components/ui/button";
import { categoryLabel } from "@/lib/category";
import { cn } from "@/lib/utils";
import type { RuleCategory } from "@/types/category";

interface CategoryFilterProps {
  /** Categories to offer — pass only the ones actually present in the current skill set, not every RuleCategory. */
  categories: RuleCategory[];
  selected: RuleCategory | null;
  onChange: (category: RuleCategory | null) => void;
  className?: string;
}

export function CategoryFilter({
  categories,
  selected,
  onChange,
  className,
}: CategoryFilterProps) {
  if (categories.length === 0) {
    return null;
  }

  return (
    <div
      role="group"
      aria-label="Filter skills by category"
      className={cn("flex flex-wrap gap-2", className)}
    >
      <Button
        type="button"
        variant={selected === null ? "default" : "outline"}
        size="sm"
        aria-pressed={selected === null}
        onClick={() => onChange(null)}
      >
        All
      </Button>
      {categories.map((category) => (
        <Button
          key={category}
          type="button"
          variant={selected === category ? "default" : "outline"}
          size="sm"
          aria-pressed={selected === category}
          onClick={() => onChange(selected === category ? null : category)}
        >
          {categoryLabel(category)}
        </Button>
      ))}
    </div>
  );
}
