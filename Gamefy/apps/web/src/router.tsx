import { createBrowserRouter, Navigate } from "react-router-dom"
import { AppShell } from "@/components/AppShell"
import { ProtectedRoute } from "@/components/ProtectedRoute"
import { CashPage } from "@/pages/CashPage"
import { DashboardPage } from "@/pages/DashboardPage"
import { LoginPage } from "@/pages/LoginPage"
import { MembersPage } from "@/pages/MembersPage"
import { SessionsPage } from "@/pages/SessionsPage"
import { StockPage } from "@/pages/StockPage"

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "/", element: <DashboardPage /> },
          { path: "/cash", element: <CashPage /> },
          { path: "/sessions", element: <SessionsPage /> },
          { path: "/stock", element: <StockPage /> },
          { path: "/members", element: <MembersPage /> },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
])
