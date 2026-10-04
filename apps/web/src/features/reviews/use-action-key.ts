"use client";
import { useRef } from "react";
/** An uncertain response keeps the same key. Only a changed request starts a new action. */
export function useActionKey() {
  const current = useRef<{ fingerprint: string; key: string } | null>(null);
  return (body: object) => {
    const fingerprint = JSON.stringify(body);
    if (!current.current || current.current.fingerprint !== fingerprint)
      current.current = { fingerprint, key: crypto.randomUUID() };
    return current.current.key;
  };
}
