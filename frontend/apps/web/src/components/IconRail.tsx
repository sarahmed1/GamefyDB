import { NavLink } from "react-router-dom"
import { Gamepad2, LayoutDashboard, Package, Receipt, Users } from "lucide-react"
import type { LucideIcon } from "lucide-react"

type NavItem = { to: string; label: string; icon: LucideIcon }

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/cash", label: "Cash transactions", icon: Receipt },
  { to: "/sessions", label: "Sessions", icon: Gamepad2 },
  { to: "/stock", label: "Stock", icon: Package },
  { to: "/members", label: "Members", icon: Users },
]

export function IconRail() {
  return (
    <nav
      aria-label="Primary navigation"
      className="flex h-screen w-14 flex-col items-center gap-1 border-r bg-card py-3"
    >
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            title={item.label}
            aria-label={item.label}
            className={({ isActive }) =>
              [
                "flex h-10 w-10 items-center justify-center rounded-md transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50",
              ].join(" ")
            }
          >
            <Icon className="h-5 w-5" />
          </NavLink>
        )
      })}
    </nav>
  )
}
