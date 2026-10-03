"use client";
import { Slot } from "@radix-ui/react-slot";
import type { ComponentProps } from "react";

type ButtonProps = ComponentProps<"button"> & {
  variant?: "primary" | "secondary" | "ghost";
  asChild?: boolean;
  staticMotion?: boolean;
};
export function Button({ variant = "primary", asChild = false, staticMotion = false, className = "", ...props }: ButtonProps) {
  const Component = asChild ? Slot : "button";
  return <Component data-static={staticMotion ? "" : undefined} className={`ui-button ui-button--${variant} ${className}`} {...props} />;
}
