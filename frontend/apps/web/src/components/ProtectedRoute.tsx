import { Navigate, Outlet } from "react-router-dom"
import { useMe } from "@/lib/auth"

export function ProtectedRoute() {
  const me = useMe()

  if (me.isPending) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        Loading…
      </div>
    )
  }

  if (!me.data) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
