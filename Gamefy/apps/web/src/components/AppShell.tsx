import { Outlet } from "react-router-dom"
import { IconRail } from "./IconRail"
import { TopBar } from "./TopBar"

export function AppShell() {
  return (
    <div className="flex min-h-screen">
      <IconRail />
      <div className="flex flex-1 flex-col">
        <TopBar />
        <main className="flex-1 overflow-auto bg-background p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
