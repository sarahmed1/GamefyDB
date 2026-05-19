import { useNavigate, useLocation } from "react-router-dom"
import { LogOut } from "lucide-react"
import { Button } from "@workspace/ui/components/button"
import { useLogout, useMe } from "@/lib/auth"

const TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/cash": "Cash transactions",
  "/sessions": "Sessions",
  "/stock": "Stock",
  "/members": "Members",
}

export function TopBar() {
  const { pathname } = useLocation()
  const me = useMe()
  const logout = useLogout()
  const navigate = useNavigate()
  const title = TITLES[pathname] ?? "GamefyDB"

  return (
    <header className="flex h-14 items-center justify-between border-b bg-card px-6">
      <h1 className="text-base font-semibold">{title}</h1>
      <div className="flex items-center gap-3">
        {me.data && <span className="text-sm text-muted-foreground">{me.data.email}</span>}
        <Button
          variant="ghost"
          size="sm"
          disabled={logout.isPending}
          onClick={async () => {
            await logout.mutateAsync()
            navigate("/login")
          }}
        >
          <LogOut className="h-4 w-4" />
          <span className="ml-2">Sign out</span>
        </Button>
      </div>
    </header>
  )
}
