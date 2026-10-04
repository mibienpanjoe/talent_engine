"use client";
import * as Primitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ComponentProps } from "react";
import { Button } from "./button";
export const Dialog = Primitive.Root;
export const DialogTrigger = Primitive.Trigger;
export function DialogTitle({ className = "", ...props }: ComponentProps<typeof Primitive.Title>) {
  return <Primitive.Title className={`dialog-title ${className}`} {...props} />;
}
export const DialogDescription = Primitive.Description;
export function DialogContent({ children, className = "", ...props }: ComponentProps<typeof Primitive.Content>) {
  return <Primitive.Portal><Primitive.Overlay className="dialog-overlay" />
    <Primitive.Content className={`dialog-content ${className}`} {...props}>
      {children}
      <Primitive.Close asChild><Button variant="ghost" className="dialog-close" aria-label="Fermer"><X aria-hidden="true" size={20} strokeWidth={1.5} /></Button></Primitive.Close>
    </Primitive.Content>
  </Primitive.Portal>;
}
