"use client";
import { UserRound } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from "../../components/ui/dialog";
import { LogoutButton } from "./logout-button";
export function AccountDialog({ login, expiresAt }: { login: string; expiresAt: string }) {
  return <Dialog><DialogTrigger asChild><Button variant="secondary" aria-label="Mon compte"><UserRound aria-hidden="true" size={18} strokeWidth={1.5} /><span className="account-label">Mon compte</span></Button></DialogTrigger>
    <DialogContent><DialogTitle className="dialog-title">Votre compte</DialogTitle><DialogDescription className="dialog-description">Vous êtes connecté en tant que {login}.</DialogDescription>
      <p className="session-expiry">Fin de session : {new Date(expiresAt).toLocaleString("fr-FR", { timeZone: "UTC", dateStyle: "short", timeStyle: "short" })} UTC.</p><LogoutButton />
    </DialogContent>
  </Dialog>;
}
