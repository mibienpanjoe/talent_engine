import Image from "next/image";
import Link from "next/link";
import mark from "../../../../assets/brand/app-icon-dark-accent.png";
export function Brand() {
  return <Link href="/" className="brand" aria-label="Talent Engine, accueil"><Image src={mark} alt="" width={48} height={48} sizes="48px" priority /><span>talent engine</span></Link>;
}
