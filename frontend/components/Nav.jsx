"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { href: "/", label: "New Test" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/verify", label: "Verify Record" },
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <nav className="nav">
      {ITEMS.map((item) => {
        const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        return (
          <Link key={item.href} href={item.href} className={`nav-item${active ? " active" : ""}`}>
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
