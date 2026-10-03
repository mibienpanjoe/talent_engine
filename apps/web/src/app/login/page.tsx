import { LoginForm } from "../../features/access/login-form";
import { SiteHeader } from "../../components/site-header";
export default function LoginPage() {
  return <><SiteHeader /><main id="main" className="page-width login-layout"><div><p className="eyebrow">Espace responsable</p><h1>Bienvenue.<br />Reprenons la revue.</h1><p>Retrouvez vos campagnes et les dossiers qui vous sont confiés.</p></div><div className="login-panel"><LoginForm /></div></main></>;
}
