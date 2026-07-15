import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset transition-colors",
  {
    variants: {
      variant: {
        default:
          "bg-s2-purple/10 text-s2-purple ring-s2-purple/30",
        success:
          "bg-green-50 text-rev-green ring-rev-green/30",
        warn:
          "bg-amber-50 text-amber-800 ring-amber-400/40",
        danger:
          "bg-red-50 text-red-700 ring-red-500/40",
        outline:
          "bg-white text-gray-700 ring-gray-300",
        muted:
          "bg-gray-100 text-gray-700 ring-gray-200",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  );
}

export { badgeVariants };
