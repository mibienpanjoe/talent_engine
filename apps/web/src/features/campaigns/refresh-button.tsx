"use client";
import { useRouter } from "next/navigation";
import { Button } from "../../components/ui/button";
export function RefreshButton() {
  const router = useRouter();
  return (
    <Button variant="secondary" onClick={() => router.refresh()}>
      Actualiser
    </Button>
  );
}
