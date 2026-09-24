import { LayoutDashboard, LogOut, Menu, Receipt, Settings, Wallet, X } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router";

import { useAuth } from "@/lib/auth";
import { cx } from "@/components/ui";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/transactions", label: "Transactions", icon: Wallet },
  { to: "/receipts", label: "Receipts", icon: Receipt },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Layout() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

  const nav = (
    <nav className="flex flex-col gap-1" aria-label="Main">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={() => setOpen(false)}
          className={({ isActive }) =>
            cx(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition",
              isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
            )
          }
        >
          <Icon className="h-4 w-4" aria-hidden />
          {label}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen lg:flex">
      {/* Sidebar (desktop) */}
      <aside className="hidden w-60 shrink-0 border-r border-slate-200 bg-white p-4 lg:flex lg:flex-col">
        <Brand />
        <div className="mt-6 flex-1">{nav}</div>
        <UserMenu name={user?.name ?? ""} email={user?.email ?? ""} onLogout={logout} />
      </aside>

      {/* Top bar (mobile) */}
      <header className="sticky top-[env(safe-area-inset-top,0px)] z-40 flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
        <Brand />
        <button
          onClick={() => setOpen((v) => !v)}
          className="rounded-md p-2 text-slate-600 hover:bg-slate-100"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </header>
      {open && (
        <div className="fixed inset-x-0 top-14 z-30 border-b border-slate-200 bg-white p-4 shadow-lg lg:hidden">
          {nav}
          <div className="mt-4 border-t border-slate-200 pt-4">
            <UserMenu name={user?.name ?? ""} email={user?.email ?? ""} onLogout={logout} />
          </div>
        </div>
      )}

      <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-2">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white">
        <Receipt className="h-4 w-4" aria-hidden />
      </span>
      <span className="text-lg font-semibold tracking-tight text-slate-900">LedgerLens</span>
    </div>
  );
}

function UserMenu({ name, email, onLogout }: { name: string; email: string; onLogout: () => void }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-slate-900">{name}</p>
        <p className="truncate text-xs text-slate-500">{email}</p>
      </div>
      <button onClick={onLogout} className="rounded-md p-2 text-slate-500 hover:bg-slate-100" aria-label="Log out" title="Log out">
        <LogOut className="h-4 w-4" />
      </button>
    </div>
  );
}
