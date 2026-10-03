import { LoginForm } from "../../features/access/login-form";
import Link from "next/link";
export default function LoginPage() {
  return <main id="main"><Link href="/">Talent Engine</Link><h1>Votre espace responsable</h1><p>Connectez-vous pour retrouver vos campagnes et vos dossiers.</p><LoginForm /></main>;
}
